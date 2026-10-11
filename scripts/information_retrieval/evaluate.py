"""Offline table recall using validation SQL as labels, never indexed evidence."""
import json
from collections import Counter

from index import SourceResolver, engine_set
from context import ContextBuilder
from planner import SYSTEM


def evaluate(index, path, limit=0):
    rows = json.loads(path.read_text())
    if limit:
        rows = rows[:limit]
    if index.encoder and rows:
        index.encoder.encode([row['question'] for row in rows])
    resolver = SourceResolver(index.tables)
    builder = ContextBuilder(index)
    results, skipped = [], []
    training_questions = {d['text'] for d in index.documents if d['kind'] == 'example'}
    for row in rows:
        expected = set()
        valid = True
        for db, query in [('db', 'query')] + [(f'db{i}', f'query{i}') for i in range(1, 4)]:
            if db in row:
                try:
                    parsed = resolver.parse(row[query], row[db])
                    expected.update(parsed['table_ids'])
                    valid &= parsed['parse_status'] in ('parsed', 'single_index_by_catalog')
                except ValueError:
                    valid = False
        if not valid or not expected:
            skipped.append(row['question_id']); continue
        engines = engine_set(row)  # Oracle engine classification: isolates retrieval.
        ranking = index.search(row['question'], 'schema', engines, 12)
        raw = [r['table_ids'][0] for r in ranking]
        context, _ = builder.fit(builder.assemble(row['question'], engines, row['question_id']), SYSTEM)
        selected = {t['table_id'] for t in context['candidate_tables']}
        result = {'question_id': row['question_id'], 'expected': sorted(expected), 'provided': sorted(selected),
                  'complete_context_recall': expected <= selected, 'irrelevant_tables': len(selected - expected),
                  'train_question_duplicate': row['question'] in training_questions,
                  'context_recall': len(expected & selected) / len(expected)}
        for k in (1, 4, 8, 12):
            result[f'recall@{k}'] = len(expected & set(raw[:k])) / len(expected)
        results.append(result)
    n = len(results)
    metrics = {key: sum(r[key] for r in results) / max(n, 1) for key in
               ('recall@1', 'recall@4', 'recall@8', 'recall@12', 'context_recall', 'complete_context_recall', 'irrelevant_tables')}
    return {'scope': 'table retrieval only; oracle engines; no validation answers supplied to index/LLM',
            'evaluated': n, 'skipped_unresolved_labels': skipped,
            'train_question_duplicates': sum(r['train_question_duplicate'] for r in results),
            'metrics': metrics, 'cases': results}
