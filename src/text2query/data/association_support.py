"""Optional evidence-provider boundary; no training or SQL dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SupportSignal:
    score: float = 0.0
    evidence: tuple[dict[str, Any], ...] = ()


@dataclass
class SupportResult:
    signals: dict[tuple[str, int], SupportSignal] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)


class AssociationSupport(Protocol):
    def prepare(
        self, knowledge: list[dict[str, Any]], *, method: str, bm25_k1: float, bm25_b: float
    ) -> SupportResult: ...
