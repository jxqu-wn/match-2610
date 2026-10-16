"""Small warmed-up CPU/CUDA comparison using identical local model inputs."""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import os
import platform
import resource
import statistics
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dtype", default="float32")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--extra-site-path", action="append", default=[])
    args = parser.parse_args()
    for path in reversed(args.extra_site_path):
        sys.path.insert(0, path)
    import numpy as np
    import torch
    from sentence_transformers import CrossEncoder, SentenceTransformer

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.manual_seed(42)
    data = json.loads(args.input.read_text())
    root = Path(__file__).resolve().parents[2]
    model_root = root.parent / "models"
    if args.output.exists():
        raise FileExistsError("Choose a new output")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "device": args.device, "dtype": args.dtype, "threads": args.threads,
        "python": platform.python_version(), "platform": platform.platform(),
        "environment": {k: importlib.metadata.version(k) for k in
                        ("torch", "transformers", "sentence-transformers", "numpy")},
        "torch_runtime_version": torch.__version__,
        "input_sha256": __import__("hashlib").sha256(args.input.read_bytes()).hexdigest(),
        "embedding_batch_size": 4, "reranker_batch_size": 2,
        "embedding_max_length": 512, "reranker_max_length": 2048,
        "embedding": {}, "reranker": [],
    }

    def sync():
        if args.device.startswith("cuda"):
            torch.cuda.synchronize()

    def save():
        result["peak_rss_gib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**2
        status = Path("/proc/self/status").read_text()
        result["rss_gib"] = int(next(s.split()[1] for s in status.splitlines() if s.startswith("VmRSS:"))) / 1024**2
        if args.device.startswith("cuda"):
            result["peak_gpu_allocated_gib"] = torch.cuda.max_memory_allocated() / 1024**3
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({"stage": "loading_embedding", "device": args.device, "threads": args.threads}), flush=True)
    started = time.perf_counter()
    encoder = SentenceTransformer(str(model_root / "Qwen3-Embedding-0.6B"), device=args.device,
                                  model_kwargs={"torch_dtype": args.dtype}, local_files_only=True)
    encoder.max_seq_length = 512
    sync()
    result["embedding_load_seconds"] = time.perf_counter() - started
    encoder.encode(data["embedding_documents"][:4], prompt="", batch_size=4, show_progress_bar=False)
    for name, texts, prompt in (
        ("documents", data["embedding_documents"], ""),
        ("queries", data["embedding_queries"], "Instruct: " + data["retrieval_instruction"] + "\nQuery: "),
    ):
        samples = []
        for _ in range(2):
            sync()
            started = time.perf_counter()
            vectors = encoder.encode(texts, prompt=prompt, batch_size=4, show_progress_bar=False,
                                     normalize_embeddings=True, convert_to_numpy=True)
            sync()
            samples.append(time.perf_counter() - started)
            assert np.isfinite(vectors).all()
        lengths = encoder.tokenizer(texts, add_special_tokens=True, truncation=True, max_length=512)["input_ids"]
        result["embedding"][name] = {"count": len(texts), "seconds": samples,
                                     "median_seconds": statistics.median(samples),
                                     "token_lengths_without_instruction": [len(ids) for ids in lengths]}
        save()
        print(json.dumps({"stage": "embedding_" + name, **result["embedding"][name]}), flush=True)
    started = time.perf_counter()
    reranker = CrossEncoder(str(model_root / "Qwen3-Reranker-0.6B"), device=args.device,
                           model_kwargs={"torch_dtype": args.dtype}, local_files_only=True,
                           trust_remote_code=False, activation_fn=torch.nn.Identity(), max_length=2048)
    sync()
    result["reranker_load_seconds"] = time.perf_counter() - started
    save()
    print(json.dumps({"stage": "both_models_loaded", "rss_gib": result["rss_gib"]}), flush=True)
    first = data["reranker_requests"][0]
    reranker.predict([(first["query"], text) for text in first["documents"][:2]],
                     prompt=data["reranker_instruction"], batch_size=2,
                     show_progress_bar=False, convert_to_numpy=True)
    for request in data["reranker_requests"]:
        sync()
        started = time.perf_counter()
        scores = reranker.predict([(request["query"], text) for text in request["documents"]],
                                  prompt=data["reranker_instruction"], batch_size=2,
                                  show_progress_bar=False, convert_to_numpy=True)
        sync()
        duration = time.perf_counter() - started
        assert np.isfinite(scores).all()
        row = {"question_id": request["question_id"], "documents": len(request["documents"]),
               "document_kinds": request["document_kinds"], "seconds": duration,
               "pairs_per_second": len(request["documents"]) / duration}
        result["reranker"].append(row)
        save()
        print(json.dumps({"stage": "reranking", **row}), flush=True)
    result["reranker_total_seconds"] = sum(r["seconds"] for r in result["reranker"])
    result["reranker_pairs"] = sum(r["documents"] for r in result["reranker"])
    result["completed"] = True
    save()
    del encoder, reranker
    gc.collect()
    print(json.dumps({"completed": True, "output": str(args.output), "peak_rss_gib": result["peak_rss_gib"]}), flush=True)


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    main()
