import copy
import json
import unittest

from build_catalog import ROOT, build, parse_es, parse_sql, read_source, split_columns
from enrich_descriptions import validate
from apply_review import apply_review
from secondary_review import apply_secondary, restore_previous


class PreprocessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = build()
        cls.tables = {t['table_id']: t for t in cls.catalog['tables']}

    def test_original_inventory(self):
        self.assertEqual(len(self.tables), 265)
        self.assertEqual(self.catalog['summary']['columns'], 1694)
        for table in self.tables.values():
            for fk in table['foreign_keys']:
                self.assertIn(fk['references']['table_id'], self.tables)

    def test_gb18030_comments_and_engine_assignment(self):
        text, encoding = read_source(ROOT / 'data/赛题8/Schema/core_schema.txt')
        self.assertEqual(encoding, 'gb18030')
        self.assertIn('最大荷载量', text)
        vessel = self.tables['MYSQL:transportation.vessel']
        self.assertEqual(next(c for c in vessel['columns'] if c['name'] == 'max_load')['description'], '最大荷载量（吨）')
        pg = self.tables['POSTGRESQL:public.vessel_ais_data']
        self.assertIsNone(pg['database'])
        self.assertEqual(pg['schema'], 'public')
        self.assertNotIn('max_load', [c['name'] for c in pg['columns']])

    def test_sqlite_nonstandard_names_and_multiline_keys(self):
        self.assertIn('R/P', [c['name'] for c in self.tables['SQLite:hockey.CombinedShutouts']['columns']])
        self.assertEqual(self.tables['SQLite:authors.Author']['primary_key'], ['Id'])
        self.assertEqual(self.tables['SQLite:hockey.Master']['primary_key'], [])
        country = next(c for c in self.tables['SQLite:hockey.Master']['columns'] if c['name'] == 'birthCountry')
        self.assertEqual(country['description'], '出生国家')
        self.assertIn(837, country['knowledge_ids'])
        position = next(c for c in self.tables['SQLite:hockey.Master']['columns'] if c['name'] == 'pos')
        self.assertEqual(position['description'], '球员场上位置')
        paragraphs = self.tables['SQLite:shakespeare.paragraphs']
        self.assertEqual(len(paragraphs['foreign_keys']), 2)
        self.assertTrue(all(fk['references']['columns'] == ['id'] for fk in paragraphs['foreign_keys']))

    def test_quoted_commas_and_index_not_column(self):
        parts = split_columns("code ENUM('A,B','C'), note TEXT COMMENT '含逗号,括号()'")
        self.assertEqual(len(parts), 2)
        text = "USE demo; CREATE TABLE x (id INT, INDEX idx (id)) COMMENT='测试表';"
        table = parse_sql(text, 'core_schema.txt', 'utf-8')[0]
        self.assertEqual([c['name'] for c in table['columns']], ['id'])
        self.assertEqual(table['description'], '测试表')

    def test_es_keyword_subfield(self):
        table = self.tables['Elasticsearch:medical_institutions']
        self.assertEqual(next(c for c in table['columns'] if c['name'] == 'name.keyword')['data_type'], 'keyword')

    def test_model_validation_rejects_fabricated_fields_and_evidence(self):
        table = {'description': None, 'columns': [{'name': 'id', 'description': None}],
                 'knowledge': [], 'training_examples': []}
        entry = {'description': '标识', 'status': 'generated', 'evidence': ['schema'], 'reason': '字段名'}
        result = {'table': entry, 'columns': [dict(entry, name='id')], 'warnings': []}
        validate(result, table)
        bad = copy.deepcopy(result)
        bad['columns'][0]['name'] = 'invented'
        with self.assertRaises(ValueError):
            validate(bad, table)
        bad = copy.deepcopy(result)
        bad['table']['evidence'] = ['knowledge:999999']
        with self.assertRaises(ValueError):
            validate(bad, table)

    def test_accepted_paraphrase_preserves_source(self):
        table = {'description': '原始表描述', 'columns': [], 'knowledge': [], 'training_examples': []}
        result = {'table': {'description': '模型扩展描述', 'status': 'accepted',
                            'evidence': ['schema'], 'reason': '原文准确'}, 'columns': [], 'warnings': []}
        validate(result, table)
        self.assertEqual(result['table']['description'], '原始表描述')
        self.assertEqual(result['table']['model_proposed_description'], '模型扩展描述')

    def test_secondary_review_is_reproducible_and_preserves_structure(self):
        directory = ROOT / 'data/preprocessed'
        catalog = json.loads((directory / 'schema_catalog.json').read_text())
        initial = json.loads((directory / 'manual_review.json').read_text())
        secondary = json.loads((directory / 'secondary_review.json').read_text())
        regenerated = copy.deepcopy(catalog)
        restore_previous(regenerated)
        apply_review(regenerated, initial)
        apply_secondary(regenerated, secondary)
        self.assertEqual(catalog, regenerated)
        self.assertEqual(catalog['description_summary']['columns_unknown'], 3)
        tables = {t['table_id']: t for t in catalog['tables']}
        for original in self.catalog['tables']:
            updated = tables[original['table_id']]
            for key in ('primary_key', 'foreign_keys', 'raw_definition'):
                self.assertEqual(original[key], updated[key])
            self.assertEqual([(c['name'], c['data_type']) for c in original['columns']],
                             [(c['name'], c['data_type']) for c in updated['columns']])
        exam = tables['MYSQL:education_2025.exam_score']
        enrollment = next(c for c in exam['columns'] if c['name'] == 'enrollment_id')
        self.assertIn('选课', enrollment['description'])
        self.assertEqual(exam['primary_key'], ['exam_score_id'])
        checkins = tables['SQLite:public_review_platform.Checkins']
        self.assertEqual(len(checkins.get('secondary_issues', [])), 1)
        label = next(c for c in checkins['columns'] if c['name'] == 'label_time_4')
        self.assertIn('04:00', label['description'])
        self.assertEqual(label['secondary_review']['status'], 'inferred')


if __name__ == '__main__':
    unittest.main()
