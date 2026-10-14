"""Recover only explicit source comments; keep schema structure unchanged."""

from copy import deepcopy

import pytest

from text2query.config import settings
from text2query.data import catalog as parser


def test_table_line_comment_crosses_only_matching_drop_and_formal_comment_wins():
    sql = """数据库：demo
-- group heading
-- 1. Local description
DROP TABLE IF EXISTS item;
CREATE TABLE item(id INT);
-- fallback description
CREATE TABLE official(id INT) COMMENT='Formal description';
-- must not cross namespace statements
USE another;
CREATE TABLE absent(id INT);
"""
    tables = parser.parse_sql(sql, "test_schema.txt", "utf-8")
    assert tables[0].description == "1. Local description"
    assert tables[0].description_source == {
        "kind": "sql_line_comment",
        "file": "test_schema.txt",
        "line": 3,
        "quote": "-- 1. Local description",
    }
    assert tables[1].description == "Formal description"
    assert tables[2].description is None


def test_table_comment_does_not_cross_other_drop_or_section_separator():
    sql = """数据库：demo
-- unrelated
DROP TABLE IF EXISTS other;
CREATE TABLE item(id INT);
-- group heading
-- =================
CREATE TABLE second(id INT);
"""
    assert all(t.description is None for t in parser.parse_sql(sql, "test_schema.txt", "utf-8"))


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_es_inline_comment_preserves_url_and_does_not_propagate_to_subfield(newline):
    source = """PUT /sample
{
 "mappings": {"properties": {
  "name": {"type":"text", "meta":{"url":"https://host/a//b"}, "fields":{"keyword":{"type":"keyword"}}}, // Literal explanation
  "plain": {"type":"integer"}
 }}
}"""
    source = source.replace("\n", newline)
    table = parser.parse_es(source, "source.txt", "utf-8")[0]
    name, keyword, plain = table.columns
    assert name.description == "Literal explanation"
    assert name.description_source["line"] == 4
    assert name.mapping["meta"]["url"] == "https://host/a//b"
    assert keyword.description is None and plain.description is None
    assert table.raw_definition == source


def test_es_ambiguous_leaf_comments_are_not_assigned_arbitrarily():
    source = """PUT /sample
{"mappings":{"properties":{
 "left":{"properties":{
  "value":{"type":"integer"} // left value
 }},
 "right":{"properties":{
  "value":{"type":"integer"}
 }}
}}}"""
    table = parser.parse_es(source, "source.txt", "utf-8")[0]
    assert all(c.description is None for c in table.columns)


def test_real_sources_restore_exactly_16_tables_and_7_fields_without_other_changes(monkeypatch):
    inputs = [(name, *parser.read_source(path)) for name, path in settings.schema_sources.items()]

    def parse_all():
        tables = []
        for name, text, encoding in inputs:
            tables.extend(parser.parse_sql(text, name, encoding))
            tables.extend(parser.parse_es(text, name, encoding))
        return [t.model_dump(by_alias=True) for t in tables]

    current = parse_all()
    original_strip = parser._json_line_comments
    with monkeypatch.context() as patch:
        patch.setattr(parser, "_preceding_table_comment", lambda *args: None)
        patch.setattr(parser, "_json_line_comments", lambda raw: (original_strip(raw)[0], []))
        baseline = parse_all()
    stripped = deepcopy(current)
    restored_tables = restored_columns = 0
    for table in stripped:
        if "description_source" in table:
            assert table["description_source"]["kind"] == "sql_line_comment"
            table.pop("description_source")
            table["description"] = table["description_origin"] = None
            restored_tables += 1
        for column in table["columns"]:
            if "description_source" in column:
                assert column["description_source"]["kind"] == "es_line_comment"
                column.pop("description_source")
                column["description"] = column["description_origin"] = None
                restored_columns += 1
    assert (restored_tables, restored_columns) == (16, 7)
    assert stripped == baseline
    by_file = {name: text.splitlines() for name, text, _ in inputs}
    for table in current:
        for item in [table, *table["columns"]]:
            if "description_source" in item:
                source = item["description_source"]
                assert source["quote"] in by_file[source["file"]][source["line"] - 1]
                assert item["description"] == source["quote"].strip()[2:].strip()


def test_es_block_boundaries_use_json_strings_and_comments():
    source = """数据库：demo
CREATE TABLE before_es(id INT);
PUT /sample
{"mappings":{"properties":{
 "name":{"type":"text","meta":{"unmatched":"}"}}, // }}} {
 "amount":{"type":"integer"}
}}}
CREATE TABLE after_es(id INT);
"""
    tables = parser.parse_sql(source, "test_schema.txt", "utf-8")
    assert [t.name for t in tables] == ["before_es", "after_es"]
    indexes = parser.parse_es(source, "test_schema.txt", "utf-8")
    assert len(indexes) == 1 and indexes[0].columns[0].mapping["meta"]["unmatched"] == "}"
    assert "CREATE TABLE after_es" not in indexes[0].raw_definition
    masked = parser._strip_es_blocks(source)
    assert len(masked) == len(source)
    assert [i for i, c in enumerate(masked) if c == "\n"] == [i for i, c in enumerate(source) if c == "\n"]
