"""Recall 参数与本地 CrossEncoder 适配；模型评分交由 sentence-transformers。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import Any

import numpy as np

from ..config import settings
from ..routing.embedding import _model_fingerprint, resolve_device


@dataclass(frozen=True)
class RecallConfig:
    bm25_top_k: int = 50
    embedding_top_k: int = 50
    rrf_k: int = 60
    rerank_top_k: int = 50
    rerank_enabled: bool = True

    def __post_init__(self) -> None:
        for name in ("bm25_top_k", "embedding_top_k", "rrf_k", "rerank_top_k"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} 必须大于 0")

    @classmethod
    def from_settings(cls) -> RecallConfig:
        return cls(
            bm25_top_k=settings.recall_bm25_top_k,
            embedding_top_k=settings.recall_embedding_top_k,
            rrf_k=settings.recall_rrf_k,
            rerank_top_k=settings.recall_rerank_top_k,
            rerank_enabled=settings.recall_rerank_enabled,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class RerankerService:
    """延迟加载本地权重，输出每个问题/文档对的原始相关性分数。

    不自行实现 Qwen 的模板或 yes/no logits；CrossEncoder 5.4+ 负责
    causal LM 和 sequence-classification 两类模型的适配。
    """

    def __init__(
        self,
        model_path: Path | str | None = None,
        *,
        device: str | None = None,
        dtype: str | None = None,
        batch_size: int | None = None,
        max_length: int | None = None,
        instruction: str | None = None,
    ) -> None:
        self.model_path = settings.path(model_path or settings.reranker_model).resolve()
        self.device = resolve_device(device or settings.reranker_device)
        selected_dtype = dtype or settings.reranker_dtype
        self.dtype = ("float32" if self.device == "cpu" else "float16") if selected_dtype == "auto" else selected_dtype
        if self.dtype not in ("float32", "float16", "bfloat16"):
            raise ValueError("reranker dtype 必须为 auto、float32、float16 或 bfloat16")
        self.batch_size = settings.reranker_batch_size if batch_size is None else batch_size
        self.max_length = settings.reranker_max_length if max_length is None else max_length
        if self.batch_size < 1 or self.max_length < 1:
            raise ValueError("reranker batch_size 和 max_length 必须大于 0")
        self.instruction = instruction or settings.reranker_instruction
        self._model: Any = None
        # 微调提交入口会并发召回；避免重复加载及共享模型并发推理。
        self._lock = RLock()

    @property
    def signature(self) -> dict[str, Any]:
        return {
            "model_path": str(self.model_path),
            "device": self.device,
            "dtype": self.dtype,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "instruction": self.instruction,
            "files": _model_fingerprint(self.model_path),
            "score_type": "raw_relevance_logit",
        }

    def _load(self) -> Any:
        if not self.model_path.is_dir():
            raise FileNotFoundError(
                f"重排模型权重目录不存在：{self.model_path}。"
                "请提供本地权重并设置 T2Q_RERANKER_MODEL；不会自动下载或跳过重排。"
            )
        from sentence_transformers import CrossEncoder
        from torch import nn

        return CrossEncoder(
            str(self.model_path),
            device=self.device,
            max_length=self.max_length,
            local_files_only=True,
            trust_remote_code=False,
            model_kwargs={"torch_dtype": self.dtype},
            activation_fn=nn.Identity(),
        )

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        with self._lock:
            if self._model is None:
                self._model = self._load()
            scores = self._model.predict(
                [(query, document) for document in documents],
                prompt=self.instruction,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        values = np.asarray(scores, dtype=np.float64)
        if values.shape not in ((len(documents),), (len(documents), 1)):
            raise ValueError("重排模型必须为每个候选返回一个相关性分数")
        values = values.reshape(-1)
        if not np.isfinite(values).all():
            raise ValueError("重排模型返回了非有限分数")
        return values.tolist()
