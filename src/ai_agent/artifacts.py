"""Artifacts and helpers for multi-agent collaboration (factbase)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    type: str  # "finding" | "hypothesis" | "question" | "decision"
    author: str  # telemetry | waveform | locator | magnitude | eq_search | critic | reporter
    timestamp_iso: str
    time_window: Optional[str] = None
    variables: Optional[List[str]] = None
    params: Optional[Dict[str, Any]] = None
    summary: str = ""
    details: Optional[str] = None
    evidence_refs: Optional[List[str]] = None
    confidence: Optional[float] = None  # 0..1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Factbase:
    facts: List[Finding] = field(default_factory=list)
    open_questions: List[Finding] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)  # simple text for MVP
    decisions: List[Finding] = field(default_factory=list)

    def add_finding(self, item: Finding) -> None:
        if item.type == "question":
            self.open_questions.append(item)
        elif item.type == "decision":
            self.decisions.append(item)
        else:
            self.facts.append(item)

    def add_contradiction(self, text: str) -> None:
        self.contradictions.append(text)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": [f.to_dict() for f in self.facts],
            "open_questions": [q.to_dict() for q in self.open_questions],
            "contradictions": list(self.contradictions),
            "decisions": [d.to_dict() for d in self.decisions],
        }
