"""Offline coverage audit of table retrieval and final selection; no API calls."""
import argparse
import json
from collections import Counter
from pathlib import Path

from business_routing import database_id
from index import DEFAULT_INDEX, ROOT, RetrievalIndex, SourceResolver, engine_set, write_json
from planner import PIPELINE_VERSION
from rank_report import relevance_ranks, rank_summary
from review_staged import CachedEncoder, expected_tables, summarize_coverage, summarize_positions


def audit(directory, index):
    selection = json.loads((directory / 'selection.json').read_text())
    validation = {r['question_id']: r for r in json.loads((ROOT / 'data/赛题8/splits/validation.json').read_text())}
    training = {r['question_id'] for r in json.loads((ROOT / 'data/赛题8/splits/train.json').read_text())}
    if training & set(validation):
        raise ValueError('Train/validation overlap')
    resolver = SourceResolver(index.tables)
    cases, positions, examples = [], [], set()
    table_rank_cases, database_rank_cases = [], []
    for item in selection:
        qid = item['question_id']
        output = json.loads((directory / f'question_{qid}.json').read_text())
        if output.get('pipeline_version') != PIPELINE_VERSION:
            raise ValueError('Unexpected pipeline version')
        context, result = output['context'], output['result']
        if context['question'] != validation[qid]['question']:
            raise ValueError('Question mismatch')
        expected = expected_tables(validation[qid], resolver)
        actual = {t['table_id'] for t in result.get('selected_tables', [])}
        provided = [t['table_id'] for t in context['candidate_tables']]
        prepared = json.loads((directory / f'prepared_{qid}.json').read_text())['context']
        initial = [t['table_id'] for t in prepared['candidate_tables']]
        initial_db = {database_id(index.tables[k]) for k in initial}
        expected_db = {database_id(index.tables[k]) for k in expected}
        provided_db = {database_id(index.tables[k]) for k in provided}
        actual_db = {database_id(index.tables[k]) for k in actual}
        hits = index.search_tables(context['question'], prepared['initial_databases'], len(index.tables))
        table_ranks, database_ranks = relevance_ranks(hits, index.tables)
        reference_table_ranks = {key: table_ranks.get(key) for key in sorted(expected)}
        reference_database_ranks = {key: database_ranks.get(key) for key in sorted(expected_db)}
        table_rank_cases.append(reference_table_ranks)
        database_rank_cases.append(reference_database_ranks)
        ranks = {k: provided.index(k) + 1 for k in expected if k in provided}
        positions.extend(ranks.values())
        for example in context.get('examples', []):
            examples.add(example['question_id'])
        cases.append({'question_id': qid, 'status': result['status'],
                      'predicted_system_types': prepared['initial_databases'],
                      'reference_system_types': engine_set(validation[qid]),
                      'system_types_exact': set(prepared['initial_databases']) == set(engine_set(validation[qid])),
                      'expected_tables': sorted(expected), 'provided_tables': provided,
                      'selected_tables': sorted(actual), 'initial_tables': initial,
                      'initial_business_databases': sorted(initial_db), 'expected_business_databases': sorted(expected_db),
                      'provided_business_databases': sorted(provided_db),
                      'selected_business_databases': sorted(actual_db),
                      'reference_table_context_positions': ranks,
                      'reference_table_relevance_ranks': reference_table_ranks,
                      'reference_database_relevance_ranks': reference_database_ranks,
                      'missing_context_tables': sorted(expected - set(provided)),
                      'missing_initial_tables': sorted(expected - set(initial)),
                      'missing_selected_tables': sorted(expected - actual),
                      'missing_selected_business_databases': sorted(expected_db - actual_db),
                      'missing_context_business_databases': sorted(expected_db - provided_db),
                      'omitted_evidence': context.get('omitted_evidence', [])})
    if not examples <= training:
        raise ValueError('Nontraining examples provided')
    return {'pipeline_version': PIPELINE_VERSION, 'questions': len(cases),
            'definitions': {'complete_rate': '每题全部参考库/表均包含于对应集合，允许额外候选',
                            'exact_rate': '每题集合与参考完全相同，不允许额外候选',
                            'occurrence_recall': '按各题参考库/表出现次数汇总命中率',
                            'business_selection': '最终所选表归属的库，不是独立业务库路由',
                            'position': '最终提供上下文中的表位置，包括外键及案例提升，非原始RRF排名',
                            'table_relevance_rank': '原问题在预测系统范围内全部表的schema RRF＋明确知识关联投影RRF排名，补检索、外键、案例提升前',
                            'database_relevance_rank': '按库内最高融合表分数降序；同分按库ID；诊断指标而非独立库检索',
                            'rank_pool': '所有预测系统合并排序；系统预测遗漏导致无排名并单列，均值不把无排名计为零'},
            'initial_context_business_databases': summarize_coverage(cases, 'expected_business_databases', 'initial_business_databases'),
            'initial_context_tables': summarize_coverage(cases, 'expected_tables', 'initial_tables'),
            'context_business_databases': summarize_coverage(cases, 'expected_business_databases', 'provided_business_databases'),
            'context_tables': summarize_coverage(cases, 'expected_tables', 'provided_tables'),
            'selected_business_databases': summarize_coverage(cases, 'expected_business_databases', 'selected_business_databases'),
            'selected_tables': summarize_coverage(cases, 'expected_tables', 'selected_tables'),
            'reference_table_context_positions': summarize_positions(positions),
            'reference_table_relevance_ranks': rank_summary(table_rank_cases),
            'reference_database_relevance_ranks': rank_summary(database_rank_cases),
            'status_counts': dict(Counter(c['status'] for c in cases)),
            'system_types_exact_questions': sum(c['system_types_exact'] for c in cases),
            'system_types_exact_rate': sum(c['system_types_exact'] for c in cases) / len(cases),
            'cropped_questions': sum(bool(c['omitted_evidence']) for c in cases),
            'leakage_audit': {'unique_training_examples_provided': len(examples),
                              'all_examples_in_training_split': True, 'train_validation_id_overlap': 0},
            'cases': cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    # Match index signature using frozen embeddings; scoring performs no inference.
    manifest = json.loads((DEFAULT_INDEX / "manifest.json").read_text())
    encoder = CachedEncoder(manifest["encoder"]) if manifest["encoder"] else None
    index = RetrievalIndex.load(DEFAULT_INDEX, encoder)
    report = audit(args.directory, index)
    write_json(args.directory / 'coverage_report.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'cases'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
