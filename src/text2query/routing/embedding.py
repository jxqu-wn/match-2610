"""语义向量服务：sentence-transformers 封装 + 内容级磁盘缓存。

替换原先手写的 transformers 池化与缓存逻辑。模型冻结，不参与微调。
缓存键包含模型文件指纹、指令、设备与精度，避免混用不同设置产生的向量。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..config import settings
from ..io import get_logger, sha256_text

logger = get_logger(__name__)


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:  # pragma: no cover - torch 属于运行时依赖
        return "cpu"


def _model_fingerprint(path: Path) -> dict[str, list[int]]:
    names = ("model.safetensors", "tokenizer.json", "config.json", "modules.json")
    fingerprint: dict[str, list[int]] = {}
    for name in names:
        target = path / name
        if target.exists():
            stat = target.stat()
            fingerprint[name] = [stat.st_size, stat.st_mtime_ns]
    return fingerprint


class EmbeddingService:
    """按指令编码文本，返回 L2 归一化向量；结果按文本缓存到 npz。"""

    def __init__(
        self,
        *,
        model_path: Path | str | None = None,
        instruction: str | None = None,
        device: str = "cpu",
        dtype: str = "auto",
        batch_size: int = 8,
        max_length: int = 256,
        cache_dir: Path | str | None = None,
    ) -> None:
        self.model_path = Path(model_path or settings.embedding_model).resolve()
        self.instruction = instruction or settings.retrieval_instruction
        self.device = resolve_device(device)
        self.dtype = ("float32" if self.device == "cpu" else "float16") if dtype == "auto" else dtype
        self.batch_size = batch_size
        self.max_length = max_length
        cache_dir = Path(cache_dir or settings.path("outputs/inference/embedding_cache"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.signature: dict[str, Any] = {
            "model_path": str(self.model_path),
            "instruction": self.instruction,
            "max_length": max_length,
            "device": self.device,
            "dtype": self.dtype,
            "normalize": True,
            "files": _model_fingerprint(self.model_path),
        }
        digest = sha256_text(str(sorted(self.signature.items(), key=lambda kv: kv[0])))[:16]
        self.cache_path = cache_dir / f"embeddings_{digest}.npz"
        self._cache: dict[str, np.ndarray] = {}
        if self.cache_path.exists():
            with np.load(self.cache_path, allow_pickle=False) as stored:
                self._cache = dict(zip(stored["texts"].tolist(), stored["vectors"]))
        self._model: Any = None

    # -- 模型加载 --------------------------------------------------------- #
    def _load(self) -> Any:
        from sentence_transformers import SentenceTransformer

        kwargs: dict[str, Any] = {"device": self.device}
        if self.dtype == "float16":
            kwargs["model_kwargs"] = {"torch_dtype": "float16"}
        model = SentenceTransformer(str(self.model_path), **kwargs)
        model.max_seq_length = self.max_length
        return model

    @property
    def model(self) -> Any:
        if self._model is None:
            self._model = self._load()
        return self._model

    # -- 编码 ------------------------------------------------------------- #
    def _save(self) -> None:
        temporary = self.cache_path.with_suffix(".tmp.npz")
        np.savez_compressed(
            temporary,
            texts=np.array(list(self._cache)),
            vectors=np.stack(list(self._cache.values())),
        )
        temporary.replace(self.cache_path)

    def encode(self, texts: list[str]) -> np.ndarray:
        missing = list(dict.fromkeys(text for text in texts if text not in self._cache))
        if missing:
            vectors = self.model.encode(
                missing,
                prompt=f"Instruct: {self.instruction}\nQuery: ",
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            for text, vector in zip(missing, np.asarray(vectors, dtype=np.float32)):
                self._cache[text] = vector
            self._save()
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        return np.stack([self._cache[text] for text in texts])
