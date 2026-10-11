import json
import unittest

from business_routing import BusinessRouter, database_id
from context import Budget, ContextBuilder
from index import RetrievalIndex, build_documents
from planner import Planner
from test_retrieval import business, plan


class SequenceClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
        self.messages = []

    def complete(self, messages, max_tokens, purpose):
        self.calls.append(purpose)
        self.messages.append(messages)
        return next(self.responses)


class StagedRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docs, _ = build_documents()
        cls.index = RetrievalIndex(docs)

    def test_business_then_tables_and_domain_isolation(self):
        client = SequenceClient([business('SQLite:professional_basketball'),
                                 json.dumps(plan('SQLite:professional_basketball.players', 'firstName'))])
        output = Planner(self.index, client, Budget(context_tokens=80000)).run('列出1970年NBA冠军球队球员全名', ['SQLite'])
        self.assertEqual(output['result']['status'], 'ready', output['result'])
        self.assertEqual(client.calls, ['business_routing', 'judgment'])
        route_context = json.loads(client.messages[0][1]['content'])
        self.assertIn('SQLite:hockey', {d['database_id'] for d in route_context['candidate_databases']})
        self.assertNotIn('candidate_tables', route_context)
        self.assertNotIn('columns', json.dumps(route_context))
        context = output['context']
        self.assertEqual({database_id(t) for t in context['candidate_tables']}, {'SQLite:professional_basketball'})
        for section in ('knowledge', 'examples'):
            for item in context[section]:
                doc = self.index.by_id[item['source_id']]
                self.assertTrue(all(database_id(self.index.tables[k]) == 'SQLite:professional_basketball' for k in doc['table_ids']))
        self.assertEqual(output['execution']['stages']['business_database']['selected'], ['SQLite:professional_basketball'])

    def test_unresolved_business_scope_stops_before_retrieval(self):
        client = SequenceClient([business(status='needs_clarification', unresolved_gaps=['年份不明确'])])
        output = Planner(self.index, client).run('统计课程数量', ['MYSQL'])
        self.assertEqual(output['result']['status'], 'needs_clarification')
        self.assertEqual(output['result']['failed_stage'], 'business_database')
        self.assertEqual(output['execution']['stages']['table_selection']['status'], 'not_run')
        self.assertEqual(output['execution']['retrieval_stats']['lexical_searches'], 0)
        self.assertEqual(client.calls, ['business_routing'])

    def test_invalid_business_database_cannot_fall_back_to_global_retrieval(self):
        client = SequenceClient([business('SQLite:not_in_catalog')])
        output = Planner(self.index, client, Budget(business_repair_calls=0)).run('球员', ['SQLite'])
        self.assertEqual(output['result']['status'], 'error')
        self.assertEqual(output['result']['failed_stage'], 'business_database')
        self.assertIn('Unknown business database', output['result']['error'])
        self.assertEqual(output['execution']['judgment_calls'], 0)
        self.assertTrue(output['execution']['business_routing'][0]['execution']['model_outputs'])

    def test_business_structure_repair_is_independent(self):
        client = SequenceClient(['invalid JSON', business('MYSQL:transportation'),
                                 json.dumps(plan('MYSQL:transportation.vessel', 'max_load'))])
        output = Planner(self.index, client).run('船舶最大载重', ['MYSQL'])
        self.assertEqual(output['result']['status'], 'ready', output['result'])
        self.assertEqual(client.calls, ['business_routing', 'business_routing_repair', 'judgment'])
        self.assertEqual(output['execution']['repair_calls'], 0)
        self.assertEqual(output['execution']['business_routing'][0]['execution']['repair_calls'], 1)

    def test_shared_dictionary_requires_selected_database(self):
        builder = ContextBuilder(self.index)
        only = builder.assemble('软件和信息技术服务业公司名称', ['MYSQL'], business_databases=['MYSQL:finance_tax'])
        self.assertEqual({database_id(t) for t in only['candidate_tables']}, {'MYSQL:finance_tax'})
        combined = builder.assemble('industry_code industry_name 公司名称', ['MYSQL'],
                                    business_databases=['MYSQL:finance_tax', 'MYSQL:common'])
        keys = {t['table_id'] for t in combined['candidate_tables']}
        self.assertIn('MYSQL:common.dict_industry', keys)
        self.assertIn('MYSQL:finance_tax.companies', keys)

    def test_cross_year_cases_are_excluded_until_both_databases_selected(self):
        builder = ContextBuilder(self.index)
        scopes = ['MYSQL:education_2024']
        context = builder.assemble('两年同名课程学分不同', ['MYSQL'], business_databases=scopes)
        for example in context['examples']:
            keys = self.index.by_id[example['source_id']]['table_ids']
            self.assertTrue(all(database_id(self.index.tables[k]) in scopes for k in keys))
        scopes.append('MYSQL:education_2025')
        context = builder.assemble('两年同名课程学分不同', ['MYSQL'], business_databases=scopes)
        self.assertEqual({database_id(t) for t in context['candidate_tables']}, set(scopes))
        self.assertTrue(any(len({database_id(self.index.tables[k]) for k in self.index.by_id[e['source_id']]['table_ids']}) == 2 for e in context['examples']))

    def test_wrong_business_gap_reroutes_before_next_table_call(self):
        gap = dict(kind='wrong_business_database', requirement='NBA篮球球员', checked_tables=[],
                   requested_evidence='职业篮球业务库', search_query='NBA basketball', allow_engine_expansion=False)
        client = SequenceClient([business('SQLite:hockey'),
            json.dumps(dict(status='insufficient_evidence', selected_tables=[], gaps=[gap])),
            business('SQLite:professional_basketball'),
            json.dumps(plan('SQLite:professional_basketball.players', 'firstName'))])
        output = Planner(self.index, client).run('NBA球员全名', ['SQLite'])
        self.assertEqual(output['result']['status'], 'ready', output['result'])
        self.assertEqual(client.calls, ['business_routing', 'judgment', 'business_routing', 'judgment'])
        self.assertEqual(output['execution']['business_routing_calls'], 2)
        self.assertEqual(output['execution']['expansion_rounds'], 1)
        self.assertEqual({database_id(t) for t in output['context']['candidate_tables']}, {'SQLite:professional_basketball'})
        second_table_context = json.loads(client.messages[-1][1]['content'])
        self.assertNotIn('schema:SQLite:hockey.', json.dumps(second_table_context))

    def test_regular_missing_attribute_does_not_reroute(self):
        gap = dict(kind='missing_attribute', requirement='球员', checked_tables=[], requested_evidence='姓名字段',
                   search_query='firstName players', allow_engine_expansion=False)
        client = SequenceClient([business('SQLite:professional_basketball'),
                                 json.dumps(dict(status='insufficient_evidence', selected_tables=[], gaps=[gap])),
                                 json.dumps(plan('SQLite:professional_basketball.players', 'firstName'))])
        output = Planner(self.index, client, Budget(context_tokens=80000)).run('NBA球员', ['SQLite'])
        self.assertEqual(output['execution']['business_routing_calls'], 1)
        self.assertEqual(output['result']['status'], 'ready', output['result'])
        self.assertEqual(client.calls, ['business_routing', 'judgment', 'judgment'])

    def test_narrowing_business_scope_is_progress_without_new_evidence(self):
        from unittest.mock import patch
        builder = ContextBuilder(self.index, Budget(context_tokens=80000))
        broad = builder.assemble('industry_code industry_name 公司名称', ['MYSQL'], business_databases=['MYSQL:finance_tax', 'MYSQL:common'])
        narrow = json.loads(json.dumps(broad))
        narrow['selected_business_databases'] = ['MYSQL:finance_tax']
        narrow['candidate_tables'] = [t for t in broad['candidate_tables'] if t['database'] == 'finance_tax']
        narrow.update(knowledge=[], examples=[], relations=[])
        gap = dict(kind='wrong_business_database', requirement='只需要公司名称', checked_tables=[],
                   requested_evidence='企业主库', search_query='公司名称', allow_engine_expansion=False)
        first = plan('MYSQL:common.dict_industry', 'industry_name')
        first.update(status='insufficient_evidence', gaps=[gap])
        client = SequenceClient([business('MYSQL:finance_tax', 'MYSQL:common'), json.dumps(first),
                                 business('MYSQL:finance_tax'), json.dumps(plan('MYSQL:finance_tax.companies', 'company_name'))])
        planner = Planner(self.index, client, Budget(context_tokens=80000))
        with patch.object(planner.builder, 'assemble', side_effect=[broad, narrow]):
            output = planner.run('公司名称', ['MYSQL'])
        self.assertEqual(output['result']['status'], 'ready', output['result'])
        self.assertEqual(output['result']['selected_business_databases'], ['MYSQL:finance_tax'])
        self.assertNotIn('schema:MYSQL:common.', json.dumps(client.messages[-1]))

    def test_business_assumptions_propagate_to_final_result(self):
        client = SequenceClient([business('MYSQL:education_2024', assumptions=['假设用户要求2024年度']),
                                 json.dumps(plan('MYSQL:education_2024.course', 'credit'))])
        output = Planner(self.index, client).run('统计课程', ['MYSQL'])
        self.assertEqual(output['result']['status'], 'ready_with_assumptions', output['result'])
        self.assertIn('假设用户要求2024年度', output['result']['assumptions'])

    def test_table_outside_scope_cannot_be_accepted(self):
        client = SequenceClient([business('SQLite:professional_basketball'),
                                 json.dumps(plan('SQLite:hockey.Master', 'playerID'))])
        output = Planner(self.index, client, Budget(repair_calls=0)).run('NBA球员', ['SQLite'])
        self.assertEqual(output['result']['status'], 'error')
        self.assertEqual(output['result']['failed_stage'], 'table_selection')
        self.assertIn('Unknown table', output['result']['error'])

    def test_namespace_ids_for_postgres_and_es(self):
        router = BusinessRouter(ContextBuilder(self.index), None)
        for engine, key in [('POSTGRESQL', 'POSTGRESQL:public'), ('Elasticsearch', 'Elasticsearch:medical_institutions')]:
            context = router.catalog('查询', [engine])
            self.assertEqual([d['database_id'] for d in context['candidate_databases']], [key])
            client = SequenceClient([business(key)])
            output = BusinessRouter(ContextBuilder(self.index), client).run('查询', [engine])
            self.assertEqual(output['result']['status'], 'ready')


if __name__ == '__main__':
    unittest.main()
