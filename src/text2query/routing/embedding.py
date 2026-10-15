"""语义向量服务：sentence-transformers 封装 + 内容级磁盘缓存。

替换原先手写的 transformers 池化与缓存逻辑。模型冻结，不参与微调。
缓存键包含模型文件指纹、指令、设备与精度，避免混用不同设置产生的向量。
"""

from __future__ import annotations

from pathlib import Path
from threading import RLock
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
    names = {
        "tokenizer.json", "tokenizer_config.json", "config.json", "modules.json",
        "config_sentence_transformers.json", "sentence_bert_config.json",
        "model.safetensors.index.json", "pytorch_model.bin.index.json",
    }
    names.update(p.name for pattern in ("*.safetensors", "pytorch_model*.bin") for p in path.glob(pattern))
    fingerprint: dict[str, list[int]] = {}
    for name in sorted(names):
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
        document_prompt: str | None = None,
    ) -> None:
        self.model_path = settings.path(model_path or settings.embedding_model).resolve()
        self.instruction = instruction or settings.retrieval_instruction
        self.device = resolve_device(device)
        self.dtype = ("float32" if self.device == "cpu" else "float16") if dtype == "auto" else dtype
        if self.dtype not in ("float32", "float16", "bfloat16"):
            raise ValueError("embedding dtype 必须为 auto、float32、float16 或 bfloat16")
        if batch_size < 1 or max_length < 1:
            raise ValueError("embedding batch_size 和 max_length 必须大于 0")
        self.batch_size = batch_size
        self.max_length = max_length
        self.document_prompt = document_prompt
        self._lock = RLock()
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
        if document_prompt is not None:
            self.signature["document_prompt"] = document_prompt
            self.signature["encoding_protocol"] = "query_document_v1"
        digest = sha256_text(str(sorted(self.signature.items(), key=lambda kv: kv[0])))[:16]
        self.cache_path = cache_dir / f"embeddings_{digest}.npz"
        self._cache: dict[str, np.ndarray] = {}
        if self.cache_path.exists():
            with np.load(self.cache_path, allow_pickle=False) as stored:
                self._cache = dict(zip(stored["texts"].tolist(), stored["vectors"]))
        self._model: Any = None

    # -- 模型加载 --------------------------------------------------------- #
    def _load(self) -> Any:
        if not self.model_path.is_dir():
            raise FileNotFoundError(
                f"Embedding 模型权重目录不存在：{self.model_path}。"
                "请提供本地权重并设置 T2Q_EMBEDDING_MODEL；不会自动下载。"
            )
        from sentence_transformers import SentenceTransformer

        kwargs: dict[str, Any] = {"device": self.device, "model_kwargs": {"torch_dtype": self.dtype}}
        model = SentenceTransformer(str(self.model_path), local_files_only=True, **kwargs)
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
        """编码查询；兼容路由训练与现有问题缓存。"""
        with self._lock:
            return self._encode(texts, prompt=f"Instruct: {self.instruction}\nQuery: ")

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        """检索文档与问题分别缓存，避免同文本复用不同 prompt 的向量。"""
        if self.document_prompt is None:
            return self.encode(texts)
        with self._lock:
            return self._encode(texts, prompt=self.document_prompt, prefix="\0document:")

    def _encode(self, texts: list[str], *, prompt: str, prefix: str = "") -> np.ndarray:
        missing = list(dict.fromkeys(text for text in texts if prefix + text not in self._cache))
        if missing:
            vectors = self.model.encode(
                missing,
                prompt=prompt,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            for text, vector in zip(missing, np.asarray(vectors, dtype=np.float32)):
                self._cache[prefix + text] = vector
            self._save()
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        return np.stack([self._cache[prefix + text] for text in texts])
