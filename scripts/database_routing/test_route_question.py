import unittest

from route_question import Router


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = Router()

    def test_hockey_paraphrase(self):
        result = self.router.route('哪个国家出生的冰球运动员最多？出生年份最多的是哪一年？')
        self.assertEqual(result['query_type'], 'single')
        self.assertEqual(result['databases'], ['SQLite'])
        self.assertIn('hockey.Master', [t['table'] for t in result['candidate_tables']])
        self.assertTrue(result['knowledge_evidence'])

    def test_cross_database_sample(self):
        sample = next(s for s in self.router.samples if 'db2' in s)
        result = self.router.route(sample['question'])
        self.assertEqual(result['query_type'], 'multi')
        self.assertEqual(result['databases'], list(dict.fromkeys([sample['db1'], sample['db2']])))

    def test_unrelated_question_abstains(self):
        result = self.router.route('火星上的独角兽如何施展魔法？')
        self.assertEqual(result['query_type'], 'unknown')
        self.assertEqual(result['databases'], [])

    def test_catalog_engines(self):
        self.assertEqual(self.router.catalog['hockey.Master']['db'], 'SQLite')
        self.assertEqual(self.router.catalog['public.vessel_ais_data']['db'], 'POSTGRESQL')
        self.assertEqual(self.router.catalog['medical_institutions']['db'], 'Elasticsearch')
        self.assertEqual(self.router.catalog['common.administrative_division']['db'], 'MYSQL')

    def test_empty_question(self):
        with self.assertRaises(ValueError):
            self.router.route(' ')


if __name__ == '__main__':
    unittest.main()
