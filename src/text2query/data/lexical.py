"""Shared raw-text features for programmatic matching and optional providers."""

from __future__ import annotations

import re


def text_features(text: str) -> list[str]:
    text = text.casefold()
    result = re.findall(r"[a-z_][a-z_0-9]*", text)
    for span in re.findall(r"[\u3400-\u9fff]+", text):
        result.extend(span[i : i + n] for n in (2, 3, 4) for i in range(len(span) - n + 1))
    return result
