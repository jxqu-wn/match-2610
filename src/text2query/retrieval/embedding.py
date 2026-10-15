"""检索专用编码配置：问题有任务指令，文档不添加 Query 前缀。"""

from __future__ import annotations

from typing import Any

from ..routing.embedding import EmbeddingService


def retrieval_encoder(**kwargs: Any) -> EmbeddingService:
    kwargs.setdefault("max_length", 512)
    kwargs.setdefault("document_prompt", "")
    return EmbeddingService(**kwargs)
