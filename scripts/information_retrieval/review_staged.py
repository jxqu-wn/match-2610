"""Local reference coverage/rank audit for a frozen three-stage live run.

No external requests or embedding inference. Business positions are LLM output
positions, not similarity ranks. Table ranks replay the original question in
each selected business database using the frozen index/query embeddings.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from business_routing import PIPELINE_VERSION, database_id
from index import ROOT, DEFAULT_INDEX, RetrievalIndex, SourceResolver, write_json
from token_report import distribution


class CachedEncoder:
    def __init__(self, signature):
        self.signature = signature
        self.model_path = Path(signature['model_path'])
        digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:16]
        path = ROOT / f'outputs/information_retrieval/embedding_cache/embeddings_{digest}.npz'
        with np.load(path, allow_pickle=False) as stored:
            self.cache = dict(zip(stored['texts'].tolist(), stored['vectors']))

    def encode(self, texts):
        missing = [t for t in texts if t not in self.cache]
        if missing:
            raise ValueError('Frozen query embeddings missing; refusing inference')
        return np.stack([self.cache[t] for t in texts])


def expected_tables(row, resolver):
    result = set()
    for db, query in [('db', 'query')] + [(f'db{i}', f'query{i}') for i in range(1, 4)]:
        if db in row:
            parsed = resolver.parse(row[query], row[db])
            if parsed['parse_status'] not in ('parsed', 'single_index_by_catalog'):
                raise ValueError('Unresolved reference label: ' + str(row['question_id']))
            result.update(parsed['table_ids'])
    if not result:
        raise ValueError('Empty reference label')
    return result


def summarize_coverage(cases, expected_key, actual_key):
    pairs = [(set(c[expected_key]), set(c[actual_key])) for c in cases]
    expected_count = sum(len(e) for e, a in pairs)
    hit_count = sum(len(e & a) for e, a in pairs)
    selected_count = sum(len(a) for e, a in pairs)
    return {'questions': len(cases), 'complete_questions': sum(e <= a for e, a in pairs),
            'complete_rate': sum(e <= a for e, a in pairs) / len(cases),
            'exact_questions': sum(e == a for e, a in pairs),
            'exact_rate': sum(e == a for e, a in pairs) / len(cases),
            'reference_occurrences': expected_count, 'hit_occurrences': hit_count,
            'occurrence_recall': hit_count / expected_count,
            'mean_question_recall': sum(len(e & a) / len(e) for e, a in pairs) / len(cases),
            'selected_occurrences': selected_count,
            'reference_precision': hit_count / selected_count if selected_count else None}


def summarize_positions(values):
    result = distribution(values)
    result['counts_by_position'] = dict(sorted(Counter(values).items()))
    result['top_k'] = {str(k): {'hits': sum(v <= k for v in values), 'rate': sum(v <= k for v in values) / len(values) if values else None}
                       for k in (1, 3, 6, 8, 12)}
    return result


def audit(directory, index):
    selection = json.loads((directory / 'selection.json').read_text())
    validation = {r['question_id']: r for r in json.loads((ROOT / 'data/赛题8/splits/validation.json').read_text())}
    training = {r['question_id']: r for r in json.loads((ROOT / 'data/赛题8/splits/train.json').read_text())}
    if set(training) & set(validation):
        raise ValueError('Train/validation overlap')
    resolver = SourceResolver(index.tables)
    cases, referenced_examples = [], set()
    for item in selection:
        qid = item['question_id']
        output = json.loads((directory / f'question_{qid}.json').read_text())
        if output.get('pipeline_version') != PIPELINE_VERSION:
            raise ValueError('Unexpected pipeline version')
        row = validation[qid]
        context, execution, result = output['context'], output['execution'], output['result']
        if context['question'] != row['question']:
            raise ValueError('Question mismatch')
        expected = expected_tables(row, resolver)
        expected_business = {database_id(index.tables[k]) for k in expected}
        route_rounds = execution['business_routing']
        first_route = route_rounds[0].get('result') or {}
        initial_business = [d['database_id'] for d in first_route.get('selected_business_databases', [])]
        applied_business = result.get('selected_business_databases', [])
        # Find the validated route actually applied to the final table context.
        matching_routes = [r for r in route_rounds if r.get('result') and
                           [d['database_id'] for d in r['result']['selected_business_databases']] == applied_business]
        final_route = matching_routes[-1]['result'] if matching_routes else {}
        final_order = [d['database_id'] for d in final_route.get('selected_business_databases', [])]
        provided = {t['table_id'] for t in context.get('candidate_tables', [])}
        selected = {t['table_id'] for t in result.get('selected_tables', [])}
        first_round = execution.get('rounds', [])[:1]
        initially_provided = {s[len('schema:'):] for s in first_round[0]['source_ids'] if s.startswith('schema:')} if first_round else set()
        table_details = []
        for position, table in enumerate(context.get('candidate_tables', []), 1):
            key = table['table_id']
            if database_id(table) not in applied_business:
                raise ValueError('Out-of-scope schema: ' + key)
            if {c[0] for c in table['columns']} != {c['name'] for c in index.tables[key]['columns']}:
                raise ValueError('Incomplete schema: ' + key)
            if key in expected:
                scope = {k for k, t in index.tables.items() if database_id(t) == database_id(table)}
                hits = index.search(row['question'], 'schema', [table['engine']], len(scope), scope_table_ids=scope)
                hit_ranks = {h['table_ids'][0]: (n + 1, h) for n, h in enumerate(hits)}
                rank, hit = hit_ranks[key]
                table_details.append({'table_id': key, 'context_position': position,
                                      'original_question_within_database_rank': rank,
                                      'semantic_rank': hit['semantic_rank'], 'keyword_rank': hit['keyword_rank'],
                                      'semantic_similarity': hit['semantic_similarity'],
                                      'retrieval_evidence': table['retrieval_evidence'], 'finally_selected': key in selected})
        for name in ('knowledge', 'examples'):
            for record in context.get(name, []):
                doc = index.by_id[record['source_id']]
                if any(database_id(index.tables[k]) not in applied_business for k in doc['table_ids']):
                    raise ValueError('Out-of-scope evidence: ' + record['source_id'])
                if name == 'examples':
                    train = training.get(record['question_id'])
                    if not train or train['question'] != record['question']:
                        raise ValueError('Non-training example')
                    for step in record['steps']:
                        if step['query'] != train[step['step']]:
                            raise ValueError('Training query mismatch')
                    referenced_examples.add(record['question_id'])
        for round_ in execution.get('rounds', []):
            for sid in round_['source_ids']:
                if sid.startswith('example:'):
                    source = index.by_id[sid]['data']
                    train = training.get(source['question_id'])
                    if not train or train['question'] != source['question'] or any(s['query'] != train[s['step']] for s in source['steps']):
                        raise ValueError('Non-training example in intermediate prompt')
                    referenced_examples.add(source['question_id'])
        cases.append({'question_id': qid, 'question': row['question'], 'status': result['status'],
                      'failed_stage': result.get('failed_stage'), 'system_type_correct': set(item['engines']) == set(row[k] for k in ('db', 'db1', 'db2', 'db3') if k in row),
                      'expected_business_databases': sorted(expected_business), 'initial_business_databases': initial_business,
                      'applied_business_databases': applied_business, 'expected_tables': sorted(expected),
                      'initially_provided_tables': sorted(initially_provided), 'provided_tables': sorted(provided),
                      'selected_tables': sorted(selected), 'missing_business_databases': sorted(expected_business - set(applied_business)),
                      'missing_context_tables': sorted(expected - provided), 'missing_selected_tables': sorted(expected - selected),
                      'extra_context_tables': sorted(provided - expected),
                      'business_output_positions': {k: final_order.index(k) + 1 for k in expected_business if k in final_order},
                      'table_details': table_details, 'expansion_rounds': execution['expansion_rounds'],
                      'business_routing_calls': execution['business_routing_calls'],
                      'omitted_evidence': context.get('omitted_evidence', [])})
    correct_tables = [t for c in cases for t in c['table_details']]
    selected_correct = [t for t in correct_tables if t['finally_selected']]
    summary = {'scope': 'Frozen real model outputs; local reference scoring only', 'questions': len(cases),
               'system_type_correct_questions': sum(c['system_type_correct'] for c in cases),
               'initial_business_coverage': summarize_coverage(cases, 'expected_business_databases', 'initial_business_databases'),
               'final_business_coverage': summarize_coverage(cases, 'expected_business_databases', 'applied_business_databases'),
               'initial_context_table_coverage': summarize_coverage(cases, 'expected_tables', 'initially_provided_tables'),
               'final_context_table_coverage': summarize_coverage(cases, 'expected_tables', 'provided_tables'),
               'final_selected_table_coverage': summarize_coverage(cases, 'expected_tables', 'selected_tables'),
               'business_position_kind': 'LLM output position only; NOT similarity/confidence ranking; input catalog is alphabetical',
               'business_correct_output_positions': summarize_positions([p for c in cases for p in c['business_output_positions'].values()]),
               'table_rank_kind': 'Original question RRF rank inside each applied business database; NOT global engine rank or supplemental-gap query rank',
               'provided_reference_table_ranks': summarize_positions([t['original_question_within_database_rank'] for t in correct_tables]),
               'provided_reference_table_context_positions': summarize_positions([t['context_position'] for t in correct_tables]),
               'selected_reference_table_ranks': summarize_positions([t['original_question_within_database_rank'] for t in selected_correct]),
               'status_counts': dict(Counter(c['status'] for c in cases)),
               'failed_stage_counts': dict(Counter(c['failed_stage'] for c in cases if c['failed_stage'])),
               'questions_with_pruning': sum(bool(c['omitted_evidence']) for c in cases),
               'leakage_audit': {'train_validation_id_overlap': 0, 'reference_sql_sent': False,
                                 'all_observed_examples_train_only': True, 'unique_observed_training_example_ids': len(referenced_examples)},
               'cases': cases}
    write_json(directory / 'coverage_rank_report.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    manifest = json.loads((DEFAULT_INDEX / 'manifest.json').read_text())
    index = RetrievalIndex.load(encoder=CachedEncoder(manifest['encoder']))
    report = audit(args.directory, index)
    print(json.dumps({k: v for k, v in report.items() if k != 'cases'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
