import unittest

from generate_submission import validate_answer
from index import SourceResolver


class SubmissionValidationTests(unittest.TestCase):
    def setUp(self):
        self.row = {'question_id': 1}
        self.resolver = SourceResolver({
            'MYSQL:sample.items': {'engine':'MYSQL','database':'sample','name':'items',
                                   'columns':[{'name':'id'}]},
            'POSTGRESQL:public.events': {'engine':'POSTGRESQL','database':'public','schema':'public',
                                        'name':'events','columns':[{'name':'item_id'}]},
        })

    def check(self, answer):
        return validate_answer({'question_id':1, **answer}, self.row, self.resolver)

    def test_valid_federated_result_placeholder(self):
        self.assertEqual([], self.check({'db1':'MYSQL','query1':'SELECT id FROM sample.items',
                                         'db2':'POSTGRESQL','query2':'SELECT item_id FROM public.events WHERE item_id IN (result)'}))

    def test_unknown_qualified_field(self):
        self.assertTrue(self.check({'db':'MYSQL','query':'SELECT t.missing FROM sample.items t'}))

    def test_write_inside_query_rejected(self):
        self.assertTrue(self.check({'db':'MYSQL','query':'SELECT id INTO outfile FROM sample.items'}))

    def test_malformed_nested_dsl_rejected(self):
        self.assertTrue(self.check({'db':'Elasticsearch','query':'{"query":{"match_all":{}}'}))

    def test_combined_engine_placeholder_rejected(self):
        self.assertTrue(self.check({'db':'MYSQL/POSTGRESQL','query':'db1/query1;db2/query2'}))


if __name__ == '__main__': unittest.main()
