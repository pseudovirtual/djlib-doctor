from __future__ import annotations

import csv
from pathlib import Path

from .plan import PlanReport


DECISION_SHEET_FIELDS = [
    "plan_type",
    "action",
    "track_id",
    "artist",
    "title",
    "confidence",
    "human_review_required",
    "reason",
    "evidence",
    "source_path",
    "candidate_path",
    "decision",
    "notes",
]


def write_decision_sheet(report: PlanReport, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DECISION_SHEET_FIELDS)
        writer.writeheader()
        for action in report.actions:
            writer.writerow(
                {
                    "plan_type": report.plan_type,
                    "action": action.action,
                    "track_id": action.track_id,
                    "artist": action.artist,
                    "title": action.title,
                    "confidence": action.confidence.value,
                    "human_review_required": "yes" if action.human_review_required else "no",
                    "reason": action.reason,
                    "evidence": " | ".join(action.evidence),
                    "source_path": action.source_path,
                    "candidate_path": action.candidate_path,
                    "decision": "",
                    "notes": "",
                }
            )
