from __future__ import annotations

import csv
from pathlib import Path

from .io_utils import read_json
from .matching import stem_key
from .plan_models import MatchConfidence, PlanAction, PlanReport


def write_plan(report: PlanReport, out_path: Path, pretty: bool = True) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.render_json(pretty=pretty) + "\n", encoding="utf-8")


def load_plan(path: Path) -> PlanReport:
    data = read_json(path)
    actions = []
    for row in data.get("actions", []):
        actions.append(
            PlanAction(
                action=row.get("action", ""),
                track_id=row.get("track_id", ""),
                artist=row.get("artist", ""),
                title=row.get("title", ""),
                confidence=MatchConfidence(row.get("confidence", "unsafe")),
                human_review_required=bool(row.get("human_review_required", True)),
                reason=row.get("reason", ""),
                evidence=tuple(row.get("evidence", [])),
                source_path=row.get("source_path", ""),
                candidate_path=row.get("candidate_path", ""),
                metadata=row.get("metadata", {}),
            )
        )
    return PlanReport(plan_type=data.get("plan_type", "unknown"), actions=tuple(actions))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_inventory(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not path.exists():
        return out
    for row in read_csv(path):
        out.setdefault(stem_key(row.get("path", "")), []).append(row.get("path", ""))
    return out


def artifact_path(snapshot_path: Path, artifact_value: str) -> Path:
    path = Path(artifact_value)
    return path if path.is_absolute() else snapshot_path.parent / path


def int_value(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0
