"""Build the 12 batch user prompts for the Deepseek Flash independent run.

Reads the frozen prompt package and writes prompts/batch-XXX.md. Uses only the
standard library and does not modify the reference inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "prompts"


def main() -> None:
    template = (PKG / "user_prompt.template.md").read_text(encoding="utf-8")
    context = (PKG / "input_context.json").read_text(encoding="utf-8")
    manifest = json.loads((PKG / "batches.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for batch in manifest["batches"]:
        target_ids = json.dumps(batch["target_table_ids"], ensure_ascii=False)
        prompt = (
            template.replace("{{BATCH_ID}}", batch["batch_id"])
            .replace("{{TARGET_TABLE_IDS_JSON}}", target_ids)
            .replace("{{INPUT_CONTEXT_JSON}}", context)
        )
        (OUT / (batch["batch_id"] + ".md")).write_text(prompt, encoding="utf-8")
        print(batch["batch_id"], len(prompt))


if __name__ == "__main__":
    main()
