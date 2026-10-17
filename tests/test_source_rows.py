import pytest

from text2query.models import Catalog
from text2query.submission.source_rows import SourceRows


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog():
    yield


def test_original_admin_row_and_inconsistent_city_name_remain_visible(tmp_path):
    path = tmp_path / "source.sql"
    original = "INSERT INTO administrative_division(id,name,city_name,level) VALUES ('110101','东城区','东城区',3);"
    path.write_text(original + "\nINSERT INTO administrative_division(id,name,city_name,level) VALUES ('110000','北京市','北京市',1);\n")
    catalog = Catalog.model_validate({"tables": [{"table_id": "MYSQL:common.administrative_division", "engine": "MYSQL",
        "database": "common", "name": "administrative_division", "columns": [
            {"name": name, "data_type": "TEXT"} for name in ["id", "name", "city_name", "level"]]}]})
    source = SourceRows(path, catalog)
    rows = source.match("北京东城区企业")
    assert rows[0]["values"]["id"] == "110101"
    assert rows[0]["values"]["city_name"] == "东城区"
    assert rows[0]["raw_sql"] == original
    assert rows[0]["source_line"] == 1
    assert len(rows) == 2
