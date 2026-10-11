"""Versioned local schema/knowledge/training indexes and RRF retrieval."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope
from explicit_knowledge import literal_references

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / 'outputs/information_retrieval/index'
INSTRUCTION = 'Retrieve database schemas, field definitions and query examples needed to answer the database question.'
VERSION = 1
SOURCES = ['data/preprocessed/schema_catalog.json', 'data/preprocessed/schema_documents.jsonl',
           'data/preprocessed/schema_extracted.json', 'data/preprocessed/manual_review.json',
           'data/preprocessed/secondary_review.json', 'data/赛题8/knowledge.json',
           'data/赛题8/splits/train.json']


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def fingerprints(root=ROOT, training_source=None):
    names = SOURCES[:6] + [training_source or SOURCES[6]]
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}


def make_encoder(model=None, device='cpu', dtype='auto', batch_size=8, max_length=512):
    sys.path.insert(0, str(ROOT / 'scripts/database_routing'))
    from embedding_classifier import LocalEncoder, DEFAULT_MODEL
    return LocalEncoder(model or DEFAULT_MODEL, ROOT / 'outputs/information_retrieval/embedding_cache',
                        batch_size=batch_size, max_length=max_length, device=device, dtype=dtype,
                        instruction=INSTRUCTION)


def terms(text):
    text = text.lower()
    result = re.findall(r'[a-z_][a-z_0-9]*|[0-9]+', text)
    for segment in re.findall(r'[\u3400-\u9fff]+', text):
        result.extend(segment[i:i + n] for n in (1, 2, 3) for i in range(len(segment) - n + 1))
    return Counter(result)


class KeywordIndex:
    def __init__(self, texts):
        self.counts = [terms(t) for t in texts]
        self.df = Counter(t for c in self.counts for t in c)
        self.lengths = [sum(c.values()) for c in self.counts]
        self.average = sum(self.lengths) / max(len(self.lengths), 1) or 1

    def score(self, query, index):
        count, length = self.counts[index], self.lengths[index]
        score = 0
        for term in terms(query):
            frequency = count.get(term, 0)
            if frequency:
                idf = math.log(1 + (len(self.counts) - self.df[term] + .5) / (self.df[term] + .5))
                score += idf * frequency * 2.2 / (frequency + 1.2 * (.25 + .75 * length / self.average))
        return score


def engine_set(row):
    return sorted({row[k] for k in ('db', 'db1', 'db2', 'db3') if k in row})


class SourceResolver:
    def __init__(self, tables):
        self.tables = tables
        self.lookup = {}
        for key, table in tables.items():
            for db in {table.get('database'), table.get('schema'), None}:
                self.lookup.setdefault((table['engine'], db.lower() if db else None,
                                        table['name'].lower()), []).append(key)

    def resolve(self, engine, table):
        values = self.lookup.get((engine, table.db.lower() or None, table.name.lower()), [])
        unique = list(dict.fromkeys(values))
        return unique[0] if len(unique) == 1 else None

    def parse(self, query, engine):
        if engine == 'Elasticsearch':
            json.loads(query)
            indices = [k for k, t in self.tables.items() if t['engine'] == engine]
            return {'table_ids': indices if len(indices) == 1 else [], 'joins': [],
                    'parse_status': 'single_index_by_catalog' if len(indices) == 1 else 'unresolved_index'}
        try:
            tree = sqlglot.parse_one(query, read={'MYSQL': 'mysql', 'SQLite': 'sqlite', 'POSTGRESQL': 'postgres'}[engine])
        except (sqlglot.errors.SqlglotError, ValueError) as error:
            return {'table_ids': [], 'joins': [], 'parse_status': 'parse_error', 'parse_error': str(error)[:200]}
        table_ids, joins, unresolved = set(), [], set()
        for scope in traverse_scope(tree):
            aliases = {}
            for alias, source in scope.sources.items():
                if isinstance(source, exp.Table):
                    key = self.resolve(engine, source)
                    if key:
                        table_ids.add(key)
                        aliases[alias.lower()] = key
                    else:
                        unresolved.add(source.sql())
            for equality in scope.expression.find_all(exp.EQ):
                if equality.find_ancestor(exp.Select) is not scope.expression:
                    continue
                left, right = equality.left, equality.right
                if not isinstance(left, exp.Column) or not isinstance(right, exp.Column):
                    continue
                left_id, right_id = aliases.get(left.table.lower()), aliases.get(right.table.lower())
                if left_id and right_id and left_id != right_id:
                    left_fields = {c['name'].lower(): c['name'] for c in self.tables[left_id]['columns']}
                    right_fields = {c['name'].lower(): c['name'] for c in self.tables[right_id]['columns']}
                    if left.name.lower() in left_fields and right.name.lower() in right_fields:
                        joins.append({'left_table': left_id, 'left_columns': [left_fields[left.name.lower()]],
                                      'right_table': right_id, 'right_columns': [right_fields[right.name.lower()]]})
        return {'table_ids': sorted(table_ids), 'joins': joins,
                'parse_status': 'unresolved_tables' if unresolved else 'parsed',
                'unresolved_tables': sorted(unresolved)}


def build_documents(root=ROOT, training_source=None):
    catalog = json.loads((root / SOURCES[0]).read_text())
    if catalog.get('enrichment', {}).get('partial'):
        raise ValueError('Partial schema catalog cannot be indexed')
    tables = {t['table_id']: t for t in catalog['tables']}
    resolver = SourceResolver(tables)
    documents = []
    for line in (root / SOURCES[1]).read_text().splitlines():
        doc = json.loads(line)
        key = doc['table_id']
        documents.append({'source_id': 'schema:' + key, 'kind': 'schema', 'engines': [tables[key]['engine']],
                          'table_ids': [key], 'text': doc['text'], 'data': tables[key]})
    if {d['table_ids'][0] for d in documents} != set(tables):
        raise ValueError('Schema documents/catalog coverage mismatch')
    unmatched_knowledge = []
    for item in json.loads((root / SOURCES[5]).read_text()):
        text = item['knowledge_text']
        related = {t['table_id'] for t in catalog['tables'] if any(
            k['knowledge_id'] == item['knowledge_id'] for k in t['knowledge'])}
        # Multi-table sentences such as “表Checkins和Days” need all named tables.
        for match in re.finditer(r'数据库([A-Za-z0-9_]+)(?:的表|中，)([^，。]+)', text):
            db, sentence = match.groups()
            for key, table in tables.items():
                if table['database'] == db and re.search(r'(?<![A-Za-z0-9_])' + re.escape(table['name']) + r'(?![A-Za-z0-9_])', sentence):
                    related.add(key)
        if not related:
            # Domain knowledge without explicit table names: link by distinctive
            # field names appearing literally, with no automatic join claim.
            identifiers = set(re.findall(r'[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+', text))
            related = {key for key, t in tables.items() if identifiers & {c['name'] for c in t['columns']}}
        if not related:
            unmatched_knowledge.append(item['knowledge_id'])
        documents.append({'source_id': f'knowledge:{item["knowledge_id"]}', 'kind': 'knowledge',
                          'engines': sorted({tables[k]['engine'] for k in related}),
                          'table_ids': sorted(related), 'text': text, 'data': item,
                          'association': 'source_or_field_reference' if related else 'unscoped'})
    parse_issues = []
    for row in json.loads((root / (training_source or SOURCES[6])).read_text()):
        steps = []
        for db_key, query_key in [('db', 'query')] + [(f'db{i}', f'query{i}') for i in range(1, 4)]:
            if db_key in row:
                try:
                    parsed = resolver.parse(row[query_key], row[db_key])
                except (ValueError, KeyError) as error:
                    parsed = {'table_ids': [], 'joins': [], 'parse_status': 'parse_error', 'parse_error': str(error)[:200]}
                steps.append({'engine': row[db_key], 'query': row[query_key], 'step': query_key, **parsed})
                if parsed['parse_status'] not in ('parsed', 'single_index_by_catalog'):
                    parse_issues.append({'question_id': row['question_id'], 'step': query_key, **parsed})
        related = sorted({key for step in steps for key in step['table_ids']})
        documents.append({'source_id': f'example:{row["question_id"]}', 'kind': 'example',
                          'engines': engine_set(row), 'table_ids': related, 'text': row['question'],
                          'data': {'question_id': row['question_id'], 'question': row['question'],
                                   'steps': steps, 'label_quality': 'training_annotation_unverified'}})
    ids = [d['source_id'] for d in documents]
    if len(ids) != len(set(ids)):
        raise ValueError('Source IDs are not unique')
    return documents, {'document_counts': dict(Counter(d['kind'] for d in documents)),
                       'example_parse_issues': parse_issues, 'unscoped_knowledge_ids': unmatched_knowledge}


class RetrievalIndex:
    def __init__(self, documents, encoder=None, vectors=None):
        self.documents = documents
        self.by_id = {d['source_id']: d for d in documents}
        self.tables = {d['table_ids'][0]: d['data'] for d in documents if d['kind'] == 'schema'}
        self.keyword = KeywordIndex([d['text'] for d in documents])
        self.encoder, self.vectors = encoder, vectors
        self.stats = {'semantic_queries': 0, 'embedding_cache_hits': 0, 'lexical_searches': 0}
        self.positions = {d['source_id']: i for i, d in enumerate(documents)}
        self.explicit_knowledge_links = {d['source_id']: literal_references(d['text'], self.tables)
                                         for d in documents if d['kind'] == 'knowledge'}

    @classmethod
    def load(cls, path=DEFAULT_INDEX, encoder=None, root=ROOT, training_source=None):
        manifest = json.loads((path / 'manifest.json').read_text())
        if manifest['version'] != VERSION or manifest['sources'] != fingerprints(root, training_source):
            raise ValueError('Index sources changed; run build-index again')
        if manifest['encoder'] != (encoder.signature if encoder else None):
            raise ValueError('Index encoder settings changed; use matching settings or rebuild')
        for name, digest in manifest.get('artifacts', {}).items():
            if hashlib.sha256((path / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Index artifact integrity mismatch: ' + name)
        documents = [json.loads(line) for line in (path / 'documents.jsonl').read_text().splitlines()]
        if len(documents) != manifest['documents']:
            raise ValueError('Index document count mismatch')
        vectors = None
        if encoder:
            with np.load(path / 'vectors.npz', allow_pickle=False) as stored:
                if stored['source_ids'].tolist() != [d['source_id'] for d in documents]:
                    raise ValueError('Vector/source alignment mismatch')
                vectors = stored['vectors']
        return cls(documents, encoder, vectors)

    @classmethod
    def build(cls, path=DEFAULT_INDEX, encoder=None, root=ROOT, training_source=None):
        documents, audit = build_documents(root, training_source)
        path.mkdir(parents=True, exist_ok=True)
        vectors = encoder.encode([d['text'] for d in documents]) if encoder else None
        (path / 'documents.jsonl').write_text(''.join(json.dumps(d, ensure_ascii=False) + '\n' for d in documents))
        if vectors is not None:
            np.savez_compressed(path / 'vectors.npz', source_ids=np.array([d['source_id'] for d in documents]), vectors=vectors)
        if encoder:
            from transformers import AutoTokenizer
            tokenizer = encoder.tokenizer or AutoTokenizer.from_pretrained(encoder.model_path, local_files_only=True)
            lengths = [len(tokenizer.encode('Instruct: ' + encoder.instruction + '\nQuery: ' + d['text'])) for d in documents]
            audit['semantic_truncation'] = {'max_length': encoder.max_length, 'affected_sources': [d['source_id'] for d, n in zip(documents, lengths) if n > encoder.max_length],
                                            'note': 'Embedding inputs are truncated; complete texts remain in keyword index and complete schemas in context.'}
        write_json(path / 'audit.json', audit)
        artifacts = ['documents.jsonl'] + (['vectors.npz'] if encoder else [])
        write_json(path / 'manifest.json', {'version': VERSION, 'sources': fingerprints(root, training_source),
                                           'encoder': encoder.signature if encoder else None,
                                           'documents': len(documents), 'audit': audit['document_counts'],
                                           'artifacts': {name: hashlib.sha256((path / name).read_bytes()).hexdigest() for name in artifacts}})
        return cls(documents, encoder, vectors)

    def search(self, query, kind, engines, limit=8, table_ids=None, exclude=(), exact_engines=False, scope_table_ids=None, explicit_only=False):
        self.stats['lexical_searches'] += 1
        selected = set(engines)
        scope = set(scope_table_ids) if scope_table_ids is not None else None
        def associated(d):
            return list(self.explicit_knowledge_links.get(d['source_id'], {})) if explicit_only else d['table_ids']
        def doc_engines(d):
            return {self.tables[k]['engine'] for k in associated(d)} if explicit_only else set(d['engines'])
        candidates = [i for i, d in enumerate(self.documents) if d['kind'] == kind and
                      (doc_engines(d) == selected if exact_engines else doc_engines(d) <= selected) and
                      bool(doc_engines(d)) and d['source_id'] not in exclude and
                      (table_ids is None or bool(set(associated(d)) & set(table_ids))) and
                      (scope is None or bool(associated(d)) and set(associated(d)) <= scope)]
        if not candidates:
            return []
        lexical = {i: self.keyword.score(query, i) for i in candidates}
        lexical_order = sorted((i for i in candidates if lexical[i] > 0), key=lambda i: (-lexical[i], self.documents[i]['source_id']))
        keyword_rank = {i: rank + 1 for rank, i in enumerate(lexical_order)}
        semantic, semantic_rank = {}, {}
        if self.encoder:
            self.stats['semantic_queries'] += 1
            self.stats['embedding_cache_hits'] += int(query in self.encoder.cache)
            vector = self.encoder.encode([query])[0]
            semantic = {i: float(self.vectors[i] @ vector) for i in candidates}
            semantic_rank = {i: rank + 1 for rank, i in enumerate(sorted(candidates, key=lambda i: (-semantic[i], self.documents[i]['source_id'])))}
        fused = {i: sum(1 / (60 + ranks[i]) for ranks in (keyword_rank, semantic_rank) if i in ranks) for i in candidates}
        ordered = sorted((i for i in candidates if fused[i] > 0), key=lambda i: (-fused[i], self.documents[i]['source_id']))[:limit]
        return [{'source_id': self.documents[i]['source_id'], 'table_ids': self.documents[i]['table_ids'],
                 'score': fused[i], 'semantic_rank': semantic_rank.get(i), 'semantic_similarity': semantic.get(i),
                 'keyword_rank': keyword_rank.get(i), 'keyword_score': lexical[i],
                 'keyword_hits': sorted(set(terms(query)) & set(self.keyword.counts[i]), key=lambda t: (-len(t), t))[:12]}
                for i in ordered]

    def search_tables(self, query, engines, limit=8, exclude=(), knowledge_limit=12):
        base = self.search(query, 'schema', engines, len(self.tables), exclude=exclude)
        # Require a literal informative query token in the original sentence.
        # The document-frequency cutoff uses the corpus only, never labels.
        explicit_docs = [d for d in self.documents if d['kind'] == 'knowledge' and self.explicit_knowledge_links.get(d['source_id'])]
        query_terms = {t for t in terms(query) if len(t) >= 2 and not t.isdigit()}
        counts = Counter(t for d in explicit_docs for t in set(terms(d['text'])))
        anchors = {t for t in query_terms if counts[t] <= max(1, len(explicit_docs) / 10)}
        eligible = {d['source_id']: sorted(anchors & set(terms(d['text']))) for d in explicit_docs}
        knowledge = [h for h in self.search(query, 'knowledge', engines, len(explicit_docs), explicit_only=True) if eligible[h['source_id']]][:knowledge_limit]
        supported = {}
        for n, hit in enumerate(knowledge, 1):
            for key, links in self.explicit_knowledge_links[hit['source_id']].items():
                if self.tables[key]['engine'] not in engines or 'schema:' + key in exclude:
                    continue
                supported.setdefault(key, []).append({'source_id': hit['source_id'], 'knowledge_rank': n,
                                                      'knowledge_score': hit['score'], 'matched_query_tokens': eligible[hit['source_id']][:8], 'literal_links': links})
        order = sorted(supported, key=lambda key: (-max(h['knowledge_score'] for h in supported[key]), key))
        ranks = {key: n for n, key in enumerate(order, 1)}
        existing = {h['table_ids'][0] for h in base}
        for key in supported:
            if key not in existing:
                base.append({'source_id': 'schema:' + key, 'table_ids': [key], 'score': 0,
                             'semantic_rank': None, 'semantic_similarity': None, 'keyword_rank': None,
                             'keyword_score': 0, 'keyword_hits': []})
        results = []
        for hit in base:
            key = hit['table_ids'][0]
            rank = ranks.get(key)
            results.append({**hit, 'schema_score': hit['score'], 'knowledge_table_rank': rank,
                            'score': hit['score'] + (0.25 / (60 + rank) if rank else 0),
                            'knowledge_support': supported.get(key, [])[:2]})
        return sorted(results, key=lambda h: (-h['score'], h['source_id']))[:limit]
