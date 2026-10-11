import json
import tempfile
import unittest
from pathlib import Path

from index import build_documents, RetrievalIndex, SourceResolver
from context import Budget, ContextBuilder, token_upper_bound
from planner import Planner, validate, SYSTEM


class Client:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def complete(self, messages, max_tokens, purpose):
        self.calls.append(purpose)
        return next(self.outputs)


def plan(table, field, **extra):
    return dict(status='ready', selected_tables=[dict(table_id=table, required_columns=[field], evidence=['schema:' + table])],
                join_plan=[], assumptions=[], unresolved_gaps=[], gaps=[], **extra)


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docs, cls.audit = build_documents()
        cls.index = RetrievalIndex(docs)
        cls.builder = ContextBuilder(cls.index)

    def test_complete_training_and_engine_filter(self):
        self.assertEqual(self.audit['document_counts']['example'], 5247)
        results = self.index.search('最大载重 max_load', 'schema', ['POSTGRESQL'])
        self.assertTrue(all(r['table_ids'][0].startswith('POSTGRESQL:') for r in results))
        self.assertEqual(self.index.search('max_load', 'schema', ['MYSQL'])[0]['table_ids'][0], 'MYSQL:transportation.vessel')

    def test_cte_aliases_are_not_physical_tables(self):
        r = SourceResolver(self.index.tables).parse('WITH x AS (SELECT * FROM hockey.Master) SELECT m.birthYear FROM x m', 'SQLite')
        self.assertEqual(r['table_ids'], ['SQLite:hockey.Master'])
        self.assertEqual(r['parse_status'], 'parsed')

    def test_budget_whole_table_and_bound(self):
        c = self.builder.assemble('hockey Master birthCountry birthYear', ['SQLite'])
        c, messages = self.builder.fit(c, SYSTEM)
        self.assertLessEqual(self.builder.estimate(messages) + 3000, self.builder.budget.context_tokens)
        for t in c['candidate_tables']:
            self.assertEqual(len(t['columns']), len(self.index.tables[t['table_id']]['columns']))
        self.assertEqual(json.loads(messages[1]['content']), c)

    def test_invalid_fields_and_hidden_evidence(self):
        c = self.builder.assemble('max_load vessel mmsi', ['MYSQL'])
        c, _ = self.builder.fit(c, SYSTEM)
        result = plan('MYSQL:transportation.vessel', 'fake_field')
        self.assertTrue(validate(result, c))
        result = plan('MYSQL:transportation.vessel', 'mmsi')
        result['selected_tables'][0]['evidence'] = ['example:999999']
        self.assertTrue(validate(result, c))

    def test_repair_and_no_query_execution(self):
        result = plan('MYSQL:transportation.vessel', 'max_load')
        client = Client(['invalid JSON', json.dumps(result)])
        output = Planner(self.index, client).run('max_load vessel mmsi', ['MYSQL'])
        self.assertEqual(output['result']['status'], 'ready')
        self.assertEqual(client.calls, ['judgment', 'repair'])

    def test_expand_wrong_classification(self):
        gap = dict(kind='missing_attribute', requirement='最大载重', checked_tables=['POSTGRESQL:public.vessel_ais_data'],
                   requested_evidence='船舶最大载重字段', search_query='max_load vessel mmsi', allow_engine_expansion=True)
        first = dict(status='need_more_evidence', selected_tables=[], gaps=[gap])
        second = plan('MYSQL:transportation.vessel', 'max_load', database_change_reason='MYSQL vessel包含缺失字段max_load')
        client = Client([json.dumps(first), json.dumps(second)])
        output = Planner(self.index, client).run('货船 MMSI 最大载重', ['POSTGRESQL'])
        self.assertEqual(output['result']['status'], 'ready', output['result'])
        self.assertEqual(output['execution']['expansion_rounds'], 1)
        self.assertEqual(output['result']['final_databases'], ['MYSQL'])

    def test_unknown_values_stops_without_expansion(self):
        gap = dict(kind='unknown_values', requirement='实际单位', checked_tables=[], requested_evidence='实际数据',
                   search_query='max_load 单位', allow_engine_expansion=False)
        client = Client([json.dumps(dict(status='need_more_evidence', selected_tables=[], gaps=[gap]))])
        output = Planner(self.index, client).run('max_load vessel mmsi', ['MYSQL'])
        self.assertEqual(output['result']['status'], 'insufficient_evidence')
        self.assertEqual(client.calls, ['judgment'])

    def test_insufficient_evidence_with_actionable_gap_expands(self):
        gap = dict(kind='missing_attribute', requirement='最大载重', checked_tables=[],
                   requested_evidence='载重字段', search_query='max_load vessel', allow_engine_expansion=True)
        client = Client([json.dumps(dict(status='insufficient_evidence', selected_tables=[], gaps=[gap])),
                         json.dumps(plan('MYSQL:transportation.vessel', 'max_load', database_change_reason='补检索发现载重表'))])
        output = Planner(self.index, client).run('货船 MMSI 最大载重', ['POSTGRESQL'])
        self.assertEqual(output['result']['status'], 'ready', output['result'])
        self.assertEqual(output['execution']['expansion_rounds'], 1)

    def test_actionable_gap_respects_budget_and_preserves_unresolved(self):
        gap = dict(kind='missing_attribute', requirement='最大载重', checked_tables=[],
                   requested_evidence='载重字段', search_query='max_load vessel', allow_engine_expansion=True)
        client = Client([json.dumps(dict(status='insufficient_evidence', selected_tables=[], gaps=[gap],
                                       unresolved_gaps=['已有未决事项']))])
        output = Planner(self.index, client, Budget(expansion_rounds=0)).run('最大载重', ['POSTGRESQL'])
        self.assertEqual(output['result']['stop_reason'], 'budget_exhausted')
        self.assertEqual(output['result']['unresolved_gaps'], ['已有未决事项', gap])
        self.assertEqual(client.calls, ['judgment'])

    def test_ambiguity_does_not_trigger_retrieval(self):
        gap = dict(kind='intent_ambiguity', requirement='统计分母', checked_tables=[],
                   requested_evidence='用户澄清统计口径', search_query='分母', allow_engine_expansion=False)
        client = Client([json.dumps(dict(status='insufficient_evidence', selected_tables=[], gaps=[gap]))])
        output = Planner(self.index, client).run('胜场多出80%', ['SQLite'])
        self.assertEqual(output['result']['status'], 'needs_clarification')
        self.assertEqual(output['result']['stop_reason'], 'no_actionable_gaps')
        self.assertEqual(output['execution']['expansion_rounds'], 0)

    def test_index_source_change_rejected(self):
        # Existing source fingerprints are checked at every load.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'manifest.json').write_text(json.dumps({'version': 1, 'sources': {}}))
            with self.assertRaisesRegex(ValueError, 'sources changed'):
                RetrievalIndex.load(path)

    def test_description_conflict_returns_original_and_review(self):
        key = 'SQLite:authors.Author'
        previous = self.builder.assemble('authors Author Id', ['SQLite'])
        gap = dict(kind='description_conflict', requirement='作者ID', checked_tables=[key],
                   requested_evidence='原始描述及复核记录', search_query='authors Author Id', allow_engine_expansion=False)
        expanded = self.builder.assemble('authors Author Id', ['SQLite'], previous=previous, requests=[gap])
        review = next(r for r in expanded['source_comparisons'] if r['table_id'] == key)
        self.assertTrue(review['raw_definition'])
        self.assertIn('Id', review['original_descriptions'])

    def test_multi_engine_quota_and_no_recursive_fk(self):
        hits = self.builder.retrieve('mmsi vessel max_load', ['MYSQL', 'POSTGRESQL'])
        self.assertLessEqual(len(hits), 8)
        self.assertTrue(any(h['table_ids'][0].startswith('MYSQL:') for h in hits))
        self.assertTrue(any(h['table_ids'][0].startswith('POSTGRESQL:') for h in hits))
        self.assertEqual(len({h['source_id'] for h in hits}), len(hits))

    def test_no_new_evidence_stops(self):
        from unittest.mock import patch
        gap = dict(kind='missing_attribute', requirement='额外字段', checked_tables=[],
                   requested_evidence='结构', search_query='same', allow_engine_expansion=False)
        client = Client([json.dumps(dict(status='need_more_evidence', selected_tables=[], gaps=[gap]))])
        planner = Planner(self.index, client)
        original = planner.builder.assemble('max_load vessel', ['MYSQL'])
        with patch.object(planner.builder, 'assemble', return_value=original):
            output = planner.run('max_load vessel', ['MYSQL'])
        self.assertEqual(output['result']['status'], 'insufficient_evidence')
        self.assertEqual(output['result']['stop_reason'], 'no_new_evidence')
        self.assertEqual(client.calls, ['judgment'])

    def test_frozen_repair_does_not_remove_evidence(self):
        c = self.builder.assemble('max_load vessel mmsi', ['MYSQL'])
        c, _ = self.builder.fit(c, SYSTEM)
        with self.assertRaisesRegex(ValueError, 'frozen evidence'):
            self.builder.fit(c, SYSTEM, [{'role': 'assistant', 'content': 'x' * 50000}], allow_pruning=False)
        self.assertTrue(c['candidate_tables'])

    def test_equivalent_gap_container_normalization(self):
        from planner import normalize_result
        result = {'gaps': [{'requested_evidence': ['表结构', '字段说明']}]}
        self.assertEqual(normalize_result(result)['gaps'][0]['requested_evidence'], '表结构; 字段说明')
        self.assertNotIn('search_query', result['gaps'][0])

    def test_assumed_ready_is_normalized_without_repair(self):
        result = plan('MYSQL:transportation.vessel', 'max_load')
        result['assumptions'] = ['数值比较需解析载重文本']
        client = Client([json.dumps(result)])
        output = Planner(self.index, client).run('max_load vessel mmsi', ['MYSQL'])
        self.assertEqual(output['result']['status'], 'ready_with_assumptions')
        self.assertEqual(client.calls, ['judgment'])

    def test_budget_invalid(self):
        with self.assertRaises(ValueError):
            Budget(context_tokens=12000, output_tokens=12000)
        with self.assertRaises(ValueError):
            Budget(repair_calls=-1)

class TokenReportTests(unittest.TestCase):
    def test_actual_usage_separated_from_uncropped_estimate(self):
        from token_report import summarize_tokens
        data = [{'context_profiles': {'raw': {'local_proxy_input_tokens': 4000}, 'fitted': {'local_proxy_input_tokens': 1000}},
                 'execution': {'transport_calls': [
                     {'success': True, 'purpose': 'judgment', 'finish_reason': 'length',
                      'usage': {'prompt_tokens': 1200, 'completion_tokens': 3000, 'total_tokens': 4200,
                                'prompt_cache_hit_tokens': 100, 'prompt_cache_miss_tokens': 1100}},
                     {'success': False, 'purpose': 'judgment'}]}}]
        report = summarize_tokens(data)
        self.assertEqual(report['actual_input_tokens']['mean'], 1200)
        self.assertEqual(report['uncropped_input_estimates']['max'], 4800)
        self.assertEqual(report['output_length_stops'], 1)
        self.assertEqual(report['cache_hit_tokens'], 100)


if __name__ == '__main__':
    unittest.main()
