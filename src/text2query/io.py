"""JSON / 哈希 / 日志等通用工具。"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from rich.logging import RichHandler


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def file_sha256(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(value: Any) -> str:
    """稳定 JSON 序列化，用于内容哈希与缓存键。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def write_json(path: Path, value: Any, *, indent: int = 2) -> None:
    """原子写入：先写临时文件再替换，避免中断产生半截产物。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    os.replace(temporary, path)


_LOGGING_READY = False


def setup_logging(level: int = logging.INFO) -> None:
    """统一的 rich 日志输出。"""
    global _LOGGING_READY
    if _LOGGING_READY:
        return
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
    _LOGGING_READY = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
