"""共享测试夹具。"""

from __future__ import annotations

import pytest

from text2query.config import settings
from text2query.data.catalog import load_catalog
from text2query.io import read_json
from text2query.retrieval.index import RetrievalIndex


@pytest.fixture(scope="session")
def catalog():
    return load_catalog()


@pytest.fixture(scope="session")
def keyword_index(tmp_path_factory, catalog):
    path = tmp_path_factory.mktemp("retrieval-index")
    return RetrievalIndex.build(
        path,
        encoder=None,
        catalog=catalog,
        knowledge=read_json(settings.knowledge),
        train_rows=read_json(settings.train_split),
    )
