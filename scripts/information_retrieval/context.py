"""Quota-aware evidence assembly, one-hop relations and bounded expansion."""
from dataclasses import asdict, dataclass
import json

from index import ROOT


@dataclass
class Budget:
    initial_tables: int = 8
    extra_tables: int = 4
    total_tables: int = 12
    knowledge: int = 12
    examples: int = 4
    expansion_rounds: int = 1
    context_tokens: int = 24000
    output_tokens: int = 3000
    repair_reserve: int = 4000
    judgment_calls: int = 2
    repair_calls: int = 1
    transport_retries: int = 2

    def __post_init__(self):
        if min(self.initial_tables, self.extra_tables, self.total_tables, self.knowledge,
               self.examples, self.context_tokens, self.output_tokens, self.judgment_calls) < 1:
            raise ValueError('Positive retrieval/context/call limits required')
        if not 0 <= self.expansion_rounds <= 1 or self.judgment_calls > 2 or self.repair_calls > 1:
            raise ValueError('First version allows at most one expansion, two judgments and one repair')
        if self.repair_reserve < 0 or self.repair_calls < 0 or self.transport_retries < 0 or self.initial_tables > self.total_tables:
            raise ValueError('Invalid call/table limits')
        if self.output_tokens >= self.context_tokens:
            raise ValueError('Output reserve must be smaller than context budget')


def token_upper_bound(messages):
    # No public exact DeepSeek tokenizer is installed. UTF-8 byte count plus
    # envelope allowance is deliberately conservative; do not call it exact.
    return sum(len(m['content'].encode('utf-8')) + 64 for m in messages) + 64


def round_robin(groups, limit):
    selected = []
    groups = [list(g) for g in groups]
    while len(selected) < limit and any(groups):
        for group in groups:
            while group and group[0]['source_id'] in {x['source_id'] for x in selected}:
                group.pop(0)
            if group and len(selected) < limit:
                selected.append(group.pop(0))
    return selected


class ContextBuilder:
    def __init__(self, index, budget=None):
        self.index, self.budget = index, budget or Budget()
        self.tokenizer = None
        if index.encoder:
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(index.encoder.model_path, local_files_only=True)

    def estimate(self, messages):
        if self.tokenizer:
            import math
            return math.ceil(1.2 * sum(len(self.tokenizer.encode(m['content'])) + 8 for m in messages)) + 256
        return token_upper_bound(messages)

    def table(self, key, retrieval=None):
        original = self.index.tables[key]
        columns = []
        for c in original['columns']:
            review = c.get('secondary_review', {})
            columns.append([c['name'], c['data_type'], c.get('nullable'), c['description'],
                            c.get('description_origin'),
                            review.get('status', c.get('description_review', {}).get('status'))])
        return {'source_id': 'schema:' + key, 'table_id': key, 'engine': original['engine'],
                'database': original.get('database'), 'schema_name': original.get('schema'),
                'name': original['name'], 'description': original['description'],
                'column_layout': ['name', 'data_type', 'nullable', 'description', 'description_origin', 'review_status'],
                'columns': columns, 'primary_key': original['primary_key'],
                'foreign_keys': original['foreign_keys'], 'constraints': original['constraints'],
                'source': original['source'],
                'retrieval_evidence': retrieval or {'reason': 'one_hop_declared_relation'},
                'review_notes': original.get('secondary_issues', [])}

    def relations(self, keys, example_ids):
        result = []
        selected = set(keys)
        for key in keys:
            for n, fk in enumerate(self.index.tables[key]['foreign_keys']):
                target = fk['references']['table_id']
                if target in selected:
                    result.append({'source_id': f'relation:declared:{key}:{n}', 'kind': 'declared_foreign_key',
                                   'left_table': key, 'left_columns': fk['columns'],
                                   'right_table': target, 'right_columns': fk['references']['columns'],
                                   'evidence': ['schema:' + key]})
        for source_id in example_ids:
            example = self.index.by_id[source_id]
            for step in example['data']['steps']:
                for n, join in enumerate(step['joins']):
                    if {join['left_table'], join['right_table']} <= selected:
                        result.append({'source_id': f'relation:example:{example["data"]["question_id"]}:{step["step"]}:{n}',
                                       'kind': 'training_case_join_unverified', **join, 'evidence': [source_id]})
            # Cross-engine IN(result) is case evidence, not a declared FK.
            steps = example['data']['steps']
            if len(steps) > 1 and all(len(s['table_ids']) == 1 for s in steps[:2]):
                first, second = steps[:2]
                left, right = first['table_ids'][0], second['table_ids'][0]
                if {left, right} <= selected and first['engine'] != second['engine']:
                    import re
                    match = re.search(r'([\w.]+)\s+IN\s*\(\s*result\s*\)', second['query'], re.I)
                    output = re.search(r'^\s*SELECT\s+(?:DISTINCT\s+)?([\w.]+)\s+FROM\b', first['query'], re.I)
                    if match and output:
                        lc, rc = output[1].split('.')[-1], match[1].split('.')[-1]
                        if lc in {c['name'] for c in self.index.tables[left]['columns']} and rc in {c['name'] for c in self.index.tables[right]['columns']}:
                            result.append({'source_id': f'relation:example:{example["data"]["question_id"]}:result_binding',
                                           'kind': 'training_case_result_binding_unverified',
                                           'left_table': left, 'left_columns': [lc], 'right_table': right,
                                           'right_columns': [rc], 'evidence': [source_id]})
        return result

    def retrieve(self, question, engines, limit=None, exclude=()):
        limit = limit or self.budget.initial_tables
        groups = [self.index.search_tables(question, [engine], limit, exclude=exclude, knowledge_limit=self.budget.knowledge) for engine in engines]
        ranking = round_robin(groups, limit)
        # Reserve two places for one-hop FK targets when available. Never
        # expand a target's own FK recursively, and count these places too.
        primary = ranking[:max(len(engines), limit - 2)]
        keys = [item['table_ids'][0] for item in primary]
        neighbors = []
        for key in keys:
            for other_key, table in self.index.tables.items():
                if table['engine'] not in engines or other_key in keys:
                    continue
                connected = any(fk['references']['table_id'] == other_key for fk in self.index.tables[key]['foreign_keys']) or any(
                    fk['references']['table_id'] == key for fk in table['foreign_keys'])
                if connected and 'schema:' + other_key not in exclude and other_key not in neighbors:
                    neighbors.append(other_key)
        for key in neighbors[:min(2, limit - len(primary))]:
            primary.append({'source_id': 'schema:' + key, 'table_ids': [key], 'reason': 'one_hop_declared_relation'})
        for item in ranking:
            if len(primary) >= limit:
                break
            if item['source_id'] not in {x['source_id'] for x in primary}:
                primary.append(item)
        return primary

    def assemble(self, question, engines, question_id=None, previous=None, requests=None):
        previous = previous or {}
        old_tables = previous.get('candidate_tables', [])
        old_ids = {'schema:' + t['table_id'] for t in old_tables}
        old_evidence = {d['source_id'] for name in ('knowledge', 'examples') for d in previous.get(name, [])}
        selected = list(engines)
        if requests:
            if any(g.get('allow_engine_expansion') for g in requests):
                selected = sorted({t['engine'] for t in self.index.tables.values()})
            limit = min(self.budget.extra_tables, self.budget.total_tables - len(old_tables))
            rankings = []
            for gap in requests:
                if gap['kind'] == 'unknown_values':
                    continue
                # Named existing tables may need more knowledge/examples,
                # rather than new schemas. The evidence search below uses
                # the gap's text and excludes already supplied sources.
                rankings.extend(self.retrieve(gap['search_query'], selected, max(1, limit), old_ids))
            ranking = round_robin([rankings], max(0, limit))
            query = ' '.join(g['search_query'] for g in requests)
        else:
            ranking = self.retrieve(question, selected)
            query = question
        candidates = old_tables + [self.table(item['table_ids'][0], item) for item in ranking]
        keys = [t['table_id'] for t in candidates]
        found_knowledge = self.index.search(query, 'knowledge', selected, self.budget.knowledge, table_ids=keys, exclude=old_evidence)
        # Supply original supporting sentences within the existing knowledge quota.
        support = {}
        for table in candidates:
            for hit in table['retrieval_evidence'].get('knowledge_support', []):
                if hit['source_id'] not in old_evidence:
                    support.setdefault(hit['source_id'], hit)
        support_hits = sorted(support.values(), key=lambda h: (h['knowledge_rank'], h['source_id']))
        found_knowledge = round_robin([support_hits, found_knowledge], self.budget.knowledge)
        knowledge = previous.get('knowledge', []) + [{'source_id': hit['source_id'], **self.index.by_id[hit['source_id']]['data']}
                                                   for hit in found_knowledge]
        groups = []
        # Exact engine-set examples take precedence, with single-engine quota
        # retained for every system in multi-engine questions.
        exact = self.index.search(query, 'example', selected, self.budget.examples, table_ids=keys,
                                  exclude=old_evidence, exact_engines=True)
        if len(engines) == 1 and not requests:
            groups = [exact]
        else:
            groups = [exact[:2]] + [self.index.search(query, 'example', [e], 2, table_ids=keys,
                                                    exclude=old_evidence, exact_engines=True) for e in selected]
        examples = previous.get('examples', []) + [{'source_id': hit['source_id'], **self.index.by_id[hit['source_id']]['data']}
                                                  for hit in round_robin(groups, self.budget.examples)]
        knowledge = (knowledge[-self.budget.knowledge:] if requests else knowledge[:self.budget.knowledge])
        examples = (examples[-self.budget.examples:] if requests else examples[:self.budget.examples])
        if examples and not requests:
            preferred_keys = [key for step in examples[0]['steps'] for key in step['table_ids'] if self.index.tables[key]['engine'] in selected]
            for key in dict.fromkeys(preferred_keys):
                if key in keys:
                    continue
                if len(candidates) >= self.budget.initial_tables:
                    removable = next((n for n in range(len(candidates)-1, len(selected)-1, -1) if candidates[n]['table_id'] not in preferred_keys), None)
                    if removable is None:
                        continue
                    candidates.pop(removable)
                candidates.append(self.table(key, {'reason': 'first_relevant_training_case', 'source_id': examples[0]['source_id']}))
                keys = [t['table_id'] for t in candidates]
        comparisons = previous.get('source_comparisons', [])
        if requests and any(g['kind'] in ('description_conflict', 'unclear_relation') for g in requests):
            extracted = json.loads((ROOT / 'data/preprocessed/schema_extracted.json').read_text())
            secondary = json.loads((ROOT / 'data/preprocessed/secondary_review.json').read_text())
            manual = json.loads((ROOT / 'data/preprocessed/manual_review.json').read_text())
            requested_keys = {key for gap in requests for key in gap['checked_tables']}
            old_comparisons = {item['source_id'] for item in comparisons}
            for table in extracted['tables']:
                key = table['table_id']
                if key not in requested_keys or 'review:' + key in old_comparisons:
                    continue
                comparisons.append({'source_id': 'review:' + key, 'table_id': key,
                                    'source': table['source'], 'raw_definition': table['raw_definition'],
                                    'original_descriptions': {c['name']: c['description'] for c in table['columns']},
                                    'manual_corrections': [r for r in manual['corrections'] if r.get('table_id') == key],
                                    'secondary_field_reviews': [r for r in secondary['field_reviews'] if r.get('table_id') == key],
                                    'special_cases': [r for r in secondary['special_cases'] if r.get('table_id') == key]})
        return {'question_id': question_id, 'question': question,
                'initial_databases': previous.get('initial_databases', engines),
                'searched_databases': selected, 'candidate_tables': candidates,
                'knowledge': knowledge, 'examples': examples, 'source_comparisons': comparisons,
                'relations': self.relations(keys, [e['source_id'] for e in examples]),
                'retrieval_budget': {**asdict(self.budget), 'remaining_expansion_rounds': 0 if previous else self.budget.expansion_rounds},
                'omitted_evidence': [], 'token_estimation': 'local_qwen_times_1.2_plus_256' if self.tokenizer else 'conservative_utf8_bytes_plus_envelope'}

    def fit(self, context, system, extra_messages=(), allow_pruning=True):
        # Drop complete low-priority evidence; never truncate individual table
        # structures silently. Restore fit copies so callers can track omissions.
        context = json.loads(json.dumps(context))
        max_input = self.budget.context_tokens - self.budget.output_tokens - (self.budget.repair_reserve if allow_pruning and self.budget.repair_calls else 0)
        preferred = set()
        if context['examples']:
            preferred.update(key for step in context['examples'][0]['steps'] for key in step['table_ids'])
        for engine in context['initial_databases']:
            first = next((t['table_id'] for t in context['candidate_tables'] if t['engine'] == engine), None)
            if first:
                preferred.add(first)
        while True:
            messages = [{'role': 'system', 'content': system},
                        {'role': 'user', 'content': json.dumps(context, ensure_ascii=False, separators=(',', ':'))}] + list(extra_messages)
            estimate = self.estimate(messages)
            if estimate <= max_input:
                context['estimated_input_tokens'] = estimate + 128
                # The estimate annotation itself must also fit.
                if estimate + 128 <= max_input:
                    messages[1]['content'] = json.dumps(context, ensure_ascii=False, separators=(',', ':'))
                    return context, messages
                context.pop('estimated_input_tokens')
            if not allow_pruning:
                raise ValueError('Repair exceeds budget with frozen evidence; no schemas removed')
            expendable = [i for i, t in enumerate(context['candidate_tables']) if t['table_id'] not in preferred]
            if expendable:
                removed = context['candidate_tables'].pop(expendable[-1])
                context['omitted_evidence'].append(removed['source_id'])
            elif len(context['knowledge']) > 2:
                removed = context['knowledge'].pop()
                context['omitted_evidence'].append(removed['source_id'])
            elif len(context['examples']) > 1:
                removed = context['examples'].pop()
                context['omitted_evidence'].append(removed['source_id'])
            elif context['examples']:
                removed = context['examples'].pop()
                context['omitted_evidence'].append(removed['source_id'])
            elif context['knowledge']:
                removed = context['knowledge'].pop()
                context['omitted_evidence'].append(removed['source_id'])
            elif context.get('source_comparisons'):
                removed = context['source_comparisons'].pop()
                context['omitted_evidence'].append(removed['source_id'])
            elif context['candidate_tables']:
                removed = context['candidate_tables'].pop()
                context['omitted_evidence'].append(removed['source_id'])
            else:
                raise ValueError('Question/instructions exceed context budget')
            keys = [t['table_id'] for t in context['candidate_tables']]
            kept = []
            for item in context['knowledge']:
                if set(self.index.by_id[item['source_id']]['table_ids']) & set(keys):
                    kept.append(item)
                else:
                    context['omitted_evidence'].append(item['source_id'])
            context['knowledge'] = kept
            kept_examples = []
            for item in context['examples']:
                if set(self.index.by_id[item['source_id']]['table_ids']) & set(keys):
                    kept_examples.append(item)
                else:
                    context['omitted_evidence'].append(item['source_id'])
            context['examples'] = kept_examples
            context['relations'] = self.relations(keys, [e['source_id'] for e in context['examples']])
