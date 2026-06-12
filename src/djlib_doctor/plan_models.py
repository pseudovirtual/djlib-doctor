from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .io_utils import render_json

PLAN_SCHEMA_VERSION = "1.0"


class MatchConfidence(str, Enum):
    EXACT = "exact"
    STRONG = "strong"
    CANDIDATE = "candidate"
    WEAK = "weak"
    UNSAFE = "unsafe"


@dataclass(frozen=True)
class PlanAction:
    action: str
    track_id: str
    artist: str
    title: str
    confidence: MatchConfidence
    human_review_required: bool
    reason: str
    evidence: tuple[str, ...]
    source_path: str = ""
    candidate_path: str = ""
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "track_id": self.track_id,
            "artist": self.artist,
            "title": self.title,
            "confidence": self.confidence.value,
            "human_review_required": self.human_review_required,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "source_path": self.source_path,
            "candidate_path": self.candidate_path,
            "metadata": self.metadata or {},
        }


@dataclass(frozen=True)
class PlanReport:
    plan_type: str
    actions: tuple[PlanAction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PLAN_SCHEMA_VERSION,
            "plan_type": self.plan_type,
            "summary": {
                "actions": len(self.actions),
                "human_review_required": sum(1 for action in self.actions if action.human_review_required),
            },
            "actions": [action.to_dict() for action in self.actions],
        }

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)

    def render_text(self) -> str:
        lines = [
            f"djlib-doctor plan: {self.plan_type}",
            f"Actions: {len(self.actions)}",
            f"Human review required: {sum(1 for action in self.actions if action.human_review_required)}",
        ]
        for action in self.actions:
            candidate = f" -> {action.candidate_path}" if action.candidate_path else ""
            lines.append(f"- {action.action} [{action.confidence.value}] {action.artist} - {action.title}{candidate}")
        return "\n".join(lines)
