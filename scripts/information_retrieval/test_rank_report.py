import unittest

from rank_report import relevance_ranks, rank_summary


class RankReportTests(unittest.TestCase):
    def test_database_max_score_and_deterministic_ties(self):
        tables = {k: {'engine': 'MYSQL', 'database': db} for k, db in [('a1', 'a'), ('a2', 'a'), ('a3', 'a'), ('b1', 'b'), ('c1', 'c')]}
        hits = [{'table_ids': [k], 'score': score} for k, score in [('b1', .8), ('c1', .8), ('a1', .5), ('a2', .4), ('a3', .3)]]
        tr, dr = relevance_ranks(hits, tables)
        self.assertEqual(dr, {'MYSQL:b': 1, 'MYSQL:c': 2, 'MYSQL:a': 3})
        self.assertEqual(tr['a1'], 3)

    def test_missing_reference_not_counted_as_rank_zero_or_topk_hit(self):
        summary = rank_summary([{'a': 1, 'b': None}, {'c': 9}])
        self.assertEqual(summary['mean'], 5)
        self.assertEqual(summary['reference_occurrences'], 3)
        self.assertEqual(summary['bins']['unranked'], 1)
        self.assertEqual(summary['top_k']['8']['reference_rate'], 1 / 3)
        self.assertEqual(summary['top_k']['8']['complete_questions'], 0)
        self.assertEqual(summary['top_k']['12']['complete_questions'], 1)


if __name__ == '__main__':
    unittest.main()
