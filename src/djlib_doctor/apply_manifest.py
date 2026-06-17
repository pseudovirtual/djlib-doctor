from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import render_json
from .plan import PlanReport
from .reviewer import ReviewLog

APPLY_MANIFEST_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ApplyManifest:
    source_plan_type: str
    operations: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": APPLY_MANIFEST_SCHEMA_VERSION,
            "mode": "dry_run_only",
            "source_plan_type": self.source_plan_type,
            "summary": {
                "operations": len(self.operations),
                "requires_human_approval": len(self.operations),
            },
            "safety": {
                "applies_changes": False,
                "requires_explicit_user_approval": True,
                "requires_backup_before_future_apply": True,
                "requires_post_apply_verification": True,
            },
            "post_apply_verification": [
                "run verify on a fresh Rekordbox XML export",
                "run compare exports against the baseline when available",
                "review decision-sheet rows for unresolved unsafe items",
            ],
            "operations": list(self.operations),
        }

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)


def build_apply_manifest(
    report: PlanReport,
    review_log: ReviewLog | None = None,
    only_reviewed: bool = False,
) -> ApplyManifest:
    operations = []
    decisions_by_id = review_log.by_review_id() if review_log else {}
    for index, action in enumerate(report.actions, 1):
        review_id = f"{report.plan_type.upper()}-{index:04d}"
        decision = decisions_by_id.get(review_id)
        if only_reviewed and decision is None:
            continue
        operations.append(
            {
                "operation_id": f"OP-{index:04d}",
                "review_id": review_id,
                "proposed_action": action.action,
                "track_id": action.track_id,
                "artist": action.artist,
                "title": action.title,
                "confidence": action.confidence.value,
                "requires_human_approval": True,
                "reason": action.reason,
                "evidence": list(action.evidence),
                "source_path": action.source_path,
                "candidate_path": action.candidate_path,
                "metadata": action.metadata or {},
                "review_decision": decision.decision if decision else "",
                "review_notes": decision.notes if decision else "",
                "status": "not_applied",
            }
        )
    return ApplyManifest(source_plan_type=report.plan_type, operations=tuple(operations))


def write_apply_manifest(manifest: ApplyManifest, out_path: Path, pretty: bool = True) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(manifest.render_json(pretty=pretty) + "\n", encoding="utf-8")
