from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .io_utils import read_json, write_json
from .plan import MatchConfidence, PlanAction, PlanReport

REVIEW_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ReviewDecision:
    review_id: str
    action: PlanAction
    decision: str
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "decision": self.decision,
            "notes": self.notes,
            "action": self.action.to_dict(),
        }


@dataclass(frozen=True)
class ReviewLog:
    source_plan_type: str
    decisions: tuple[ReviewDecision, ...]

    def by_review_id(self) -> dict[str, ReviewDecision]:
        return {decision.review_id: decision for decision in self.decisions}


def load_review_log(path: Path) -> ReviewLog:
    data = read_json(path)
    return ReviewLog(
        source_plan_type=data.get("source_plan_type", ""),
        decisions=tuple(_decision_from_dict(row) for row in data.get("decisions", [])),
    )


def write_review_log(report: PlanReport, decisions: tuple[ReviewDecision, ...], out_path: Path) -> None:
    write_json(
        out_path,
        {
            "schema_version": REVIEW_SCHEMA_VERSION,
            "source_plan_type": report.plan_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "plan_actions": len(report.actions),
                "decisions": len(decisions),
                "unreviewed": len(report.actions) - len(decisions),
            },
            "decisions": [decision.to_dict() for decision in decisions],
        },
    )


def _decision_from_dict(row: dict[str, object]) -> ReviewDecision:
    return ReviewDecision(
        review_id=row.get("review_id", ""),
        action=_action_from_dict(row.get("action", {})),
        decision=row.get("decision", ""),
        notes=row.get("notes", ""),
    )


def _action_from_dict(data: dict[str, object]) -> PlanAction:
    metadata = data.get("metadata", {})
    return PlanAction(
        action=str(data.get("action", "")),
        track_id=str(data.get("track_id", "")),
        artist=str(data.get("artist", "")),
        title=str(data.get("title", "")),
        confidence=MatchConfidence(str(data.get("confidence", "unsafe"))),
        human_review_required=bool(data.get("human_review_required", True)),
        reason=str(data.get("reason", "")),
        evidence=tuple(str(item) for item in data.get("evidence", [])),
        source_path=str(data.get("source_path", "")),
        candidate_path=str(data.get("candidate_path", "")),
        metadata=metadata if isinstance(metadata, dict) else {},
    )
