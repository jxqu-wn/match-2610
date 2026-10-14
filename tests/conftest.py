"""共享测试夹具。"""

from __future__ import annotations

import pytest

from text2query.config import settings
from text2query.data.catalog import build_catalog, load_catalog
from text2query.data.split import build_split
from text2query.io import read_json
from text2query.retrieval.index import RetrievalIndex


@pytest.fixture(scope="session", autouse=True)
def prepared_catalog(tmp_path_factory):
    """从原始输入重建划分和目录；全部中间产物只写到临时目录。"""
    previous_preprocessed = settings.preprocessed_dir
    previous_splits = settings.splits_dir
    settings.preprocessed_dir = tmp_path_factory.mktemp("preprocessed")
    settings.splits_dir = tmp_path_factory.mktemp("splits")
    try:
        build_split()
        build_catalog(persist=True)
        yield
    finally:
        settings.preprocessed_dir = previous_preprocessed
        settings.splits_dir = previous_splits


@pytest.fixture(scope="session")
def catalog(prepared_catalog):
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
