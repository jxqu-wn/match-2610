import unittest

from explicit_knowledge import literal_references
from index import RetrievalIndex


def table(database, name, field='value', engine='MYSQL'):
    return {'database': database, 'name': name, 'columns': [{'name': field}], 'engine': engine}


class ExplicitKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tables = {'MYSQL:a.course': table('a', 'course', 'credit'),
                       'MYSQL:b.course': table('b', 'course', 'credit'),
                       'MYSQL:a.Rolee': table('a', 'Rolee', 'Role_Desc')}

    def test_field_names_and_ambiguous_table_field_never_resolve(self):
        self.assertEqual(literal_references('credit >= 3.5；课程学分；course.credit', self.tables), {})
        self.assertEqual(literal_references('Keeper表示守门员', self.tables), {})

    def test_database_scoped_names_and_qualified_references_resolve(self):
        links = literal_references('在数据库a的表course中，credit表示学分；表Rolee保存角色。', self.tables)
        self.assertEqual(set(links), {'MYSQL:a.course', 'MYSQL:a.Rolee'})
        self.assertEqual(set(literal_references('b.course.credit表示学分', self.tables)), {'MYSQL:b.course'})

    def test_qualified_other_database_not_attributed_to_current_scope(self):
        self.assertEqual(set(literal_references('数据库a中，b.course.credit是学分。', self.tables)), {'MYSQL:b.course'})

    def test_ambiguous_namespace_across_engines_not_resolved(self):
        tables = {**self.tables, 'SQLite:a.course': table('a', 'course', 'credit', 'SQLite')}
        self.assertEqual(literal_references('数据库a的表course；a.course.credit', tables), {})

    def test_values_and_bare_fields_matching_table_names_do_not_link(self):
        tables = {'MYSQL:a.genre': table('a', 'genre', 'genre_name'),
                  'MYSQL:a.platform': table('a', 'platform', 'id'),
                  'MYSQL:a.Person': table('a', 'Person', 'id')}
        links = literal_references("数据库a的表genre中，genre_name取值'Platform'；person为人员名称。", tables)
        self.assertEqual(set(links), {'MYSQL:a.genre'})

    def test_listed_tables_and_literal_target_references_link(self):
        links = literal_references('数据库a的表course和Rolee中；字段role_id关联Rolee。', self.tables)
        self.assertEqual(set(links), {'MYSQL:a.course', 'MYSQL:a.Rolee'})

    def test_unqualified_table_field_requires_existing_field_and_unique_table(self):
        self.assertEqual(set(literal_references('Rolee.Role_Desc表示角色', self.tables)), {'MYSQL:a.Rolee'})
        self.assertEqual(literal_references('Rolee.unknown', self.tables), {})

    def test_scope_does_not_leak_to_another_database(self):
        links = literal_references('数据库a的表Rolee。数据库b的表course。', self.tables)
        self.assertEqual(set(links), {'MYSQL:a.Rolee', 'MYSQL:b.course'})

    def test_inferred_old_association_cannot_promote_table(self):
        docs = [{'source_id': 'schema:'+key, 'kind': 'schema', 'engines': ['MYSQL'],
                 'table_ids': [key], 'text': t['name'], 'data': t} for key, t in self.tables.items()]
        docs += [{'source_id': 'knowledge:1', 'kind': 'knowledge', 'engines': ['MYSQL'],
                  'table_ids': ['MYSQL:a.course'], 'text': 'credit 守门员 Keeper', 'data': {}},
                 {'source_id': 'knowledge:2', 'kind': 'knowledge', 'engines': ['MYSQL'],
                  'table_ids': ['MYSQL:a.Rolee'], 'text': '在数据库a的表Rolee中，Keeper表示守门员', 'data': {}}]
        index = RetrievalIndex(docs)
        hits = index.search_tables('Keeper 守门员', ['MYSQL'])
        self.assertTrue(hits)
        self.assertEqual(hits[0]['table_ids'], ['MYSQL:a.Rolee'])
        self.assertEqual({s['source_id'] for h in hits for s in h['knowledge_support']}, {'knowledge:2'})
        self.assertEqual(index.search_tables('Keeper', ['POSTGRESQL']), [])
        self.assertFalse(any(h['table_ids']==['MYSQL:a.Rolee'] for h in index.search_tables('Keeper', ['MYSQL'], exclude=['schema:MYSQL:a.Rolee'])))


if __name__ == '__main__':
    unittest.main()
