"""Evidence-based database routing baseline; standard library only.

Only splits/train.json is retrieved. Validation and test labels are never read.
Similarity is a retrieval score, not a calibrated probability.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def tokens(text):
    text = re.sub(r"\s+", "", text.lower())
    return Counter(text[i:i + 2] for i in range(len(text) - 1))


class Index:
    def __init__(self, documents):
        counts = [tokens(text) for text in documents]
        df = Counter(term for count in counts for term in count)
        self.idf = {term: math.log((len(counts) + 1) / (n + 1)) + 1
                    for term, n in df.items()}
        self.vectors = [self.vector(count) for count in counts]

    def vector(self, count):
        weights = {term: (1 + math.log(n)) * self.idf[term]
                   for term, n in count.items() if term in self.idf}
        norm = math.sqrt(sum(w * w for w in weights.values())) or 1
        return {term: w / norm for term, w in weights.items()}

    def search(self, question, limit=5):
        vector = self.vector(tokens(question))
        scores = [(sum(w * other.get(term, 0) for term, w in vector.items()), i)
                  for i, other in enumerate(self.vectors)]
        return sorted(scores, key=lambda item: (-item[0], item[1]))[:limit]


def load_catalog(data):
    catalog = {}
    for filename in ('bird_schemas.txt', 'commom_schema.txt', 'core_schema.txt'):
        path = data / '赛题8' / 'Schema' / filename
        text = path.read_text(encoding='utf-8', errors='replace')
        database = None
        current = None
        for line in text.splitlines():
            match = re.search(r'数据库:\s*(\w+)|^USE\s+(\w+)', line)
            if match:
                database = match.group(1) or match.group(2)
                current = None
            match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?["`]?([\w.]+)', line)
            if match:
                table = match.group(1)
                engine = 'SQLite' if filename == 'bird_schemas.txt' else 'MYSQL'
                if table.startswith('public.'):
                    engine, dbname = 'POSTGRESQL', 'public'
                else:
                    dbname = database
                if dbname:
                    current = f'{dbname}.{table.split(".")[-1]}'
                    catalog[current] = {'db': engine, 'columns': [],
                                        'schema_source': str(path.relative_to(ROOT))}
            elif current:
                field = re.match(r'\s+["`]?([\w]+)["`]?\s+(TEXT|INTEGER|INT|BIGINT|VARCHAR|CHAR|DATE|DECIMAL|REAL|NUMERIC|DOUBLE|TIMESTAMP|BOOLEAN|ENUM|TINYINT)\b', line, re.I)
                if field:
                    catalog[current]['columns'].append(field.group(1))
        for name in re.findall(r'^PUT\s+/(\w+)', text, re.M):
            catalog[name] = {'db': 'Elasticsearch', 'columns': [],
                             'schema_source': str(path.relative_to(ROOT))}
    return catalog


class Router:
    def __init__(self, data=ROOT / 'data'):
        self.catalog = load_catalog(data)
        self.samples = json.loads((data / '赛题8/splits/train.json').read_text())
        self.knowledge = json.loads((data / '赛题8/knowledge.json').read_text())
        self.sample_index = Index([item['question'] for item in self.samples])
        self.knowledge_index = Index([item['knowledge_text'] for item in self.knowledge])

    def route(self, question, question_id=None):
        if not question.strip():
            raise ValueError('问题不能为空')
        neighbors = self.sample_index.search(question)
        best_score, best_index = neighbors[0]
        sample = self.samples[best_index]
        steps = ([('db', 'query')] if 'db' in sample else
                 [(f'db{i}', f'query{i}') for i in range(1, 10) if f'db{i}' in sample])
        engines = list(dict.fromkeys(sample[db] for db, _ in steps))
        known_tables = []
        for db, query in steps:
            sql = sample.get(query, '')
            for table, metadata in self.catalog.items():
                name = table if metadata['db'] in ('SQLite', 'MYSQL') else table.split('.')[-1]
                if metadata['db'] == sample[db] and re.search(
                        r'(?<![\w])' + re.escape(name) + r'(?![\w])', sql, re.I):
                    if table not in known_tables:
                        known_tables.append(table)
        evidence = []
        for score, i in self.knowledge_index.search(question, len(self.knowledge)):
            item = self.knowledge[i]
            match = re.search(r'数据库([A-Za-z0-9_]+)的表([A-Za-z0-9_]+)', item['knowledge_text'])
            if match and f'{match[1]}.{match[2]}' in known_tables:
                evidence.append(dict(item, similarity=round(score, 4)))
        # Do not silently promote weak retrieval to a definitive decision.
        accepted = best_score >= 0.45 and bool(known_tables)
        return {
            'question_id': question_id, 'question': question,
            'query_type': ('single' if len(engines) == 1 else 'multi') if accepted else 'unknown',
            'databases': engines if accepted else [],
            'status': 'retrieval_supported' if accepted else 'needs_review',
            'retrieval_score': round(best_score, 4),
            'candidate_databases': engines,
            'candidate_tables': [dict(table=table, **self.catalog[table]) for table in known_tables],
            'knowledge_evidence': evidence[:6],
            'similar_questions': [
                {'question_id': self.samples[i]['question_id'],
                 'question': self.samples[i]['question'], 'similarity': round(score, 4),
                 'databases': [self.samples[i][key] for key in ('db', 'db1', 'db2', 'db3')
                               if key in self.samples[i]]}
                for score, i in neighbors],
            'notes': ['基于训练样例检索的候选路由，尚未验证问题全部条件的覆盖情况。',
                      '多库执行顺序与结果绑定需由后续查询计划模块确认。']
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question')
    parser.add_argument('--question-id', type=int)
    args = parser.parse_args()
    print(json.dumps(Router().route(args.question, args.question_id), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
