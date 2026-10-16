"""核对下载文件与原 Git LFS 指针的大小、SHA256；不加载或测试模型。"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path(__file__).resolve().parents[1] / "docs/model_weights_manifest.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sizes-only", action="store_true", help="仅查看下载大小，不计算 SHA256")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    files = []
    for model in manifest["models"]:
        directory = Path(model["directory"])
        if not directory.is_absolute():
            directory = Path(__file__).resolve().parents[1] / directory
        for expected in model["files"]:
            path = directory.resolve() / expected["file"]
            size = path.stat().st_size if path.is_file() else None
            digest = None
            if size == expected["bytes"] and not args.sizes_only:
                hasher = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                        hasher.update(chunk)
                digest = hasher.hexdigest()
            size_matches = size == expected["bytes"]
            hash_matches = digest == expected["sha256"] if digest is not None else None
            row = {
                "repo": model["repo"], "revision": model["revision"], "file": str(path),
                "expected_bytes": expected["bytes"], "actual_bytes": size,
                "expected_sha256": expected["sha256"], "actual_sha256": digest,
                "size_matches": size_matches, "hash_matches": hash_matches,
            }
            files.append(row)
            status = "size-ok" if args.sizes_only and size_matches else (
                "verified" if size_matches and hash_matches else "incomplete-or-mismatch"
            )
            print(f"{model['repo']} {expected['file']}: {status}", flush=True)
    result = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "mode": "sizes_only" if args.sizes_only else "sha256",
        "all_sizes_match": bool(files) and all(row["size_matches"] for row in files),
        "all_hashes_match": bool(files) and all(row["hash_matches"] is True for row in files),
        "total_expected_bytes": sum(row["expected_bytes"] for row in files),
        "files": files,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if (result["all_sizes_match"] if args.sizes_only else result["all_hashes_match"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
