from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from .io_utils import read_json, write_json

CLEANUP_APPLY_SCHEMA_VERSION = "1.0"
ACTIONABLE_DECISIONS = {"manual_match", "find_clean_keeper", "approve"}
SKIP_DECISIONS = {
    "",
    "skip",
    "keep_for_now",
    "needs_listening",
    "needs_investigation",
    "needs_probe_review",
    "accept_difference",
}


def build_rekordbox_cleanup_operations(apply_manifest: Path, out_path: Path) -> Path:
    manifest = read_json(apply_manifest)
    _require_apply_manifest(manifest)
    operations = []
    for row in manifest.get("operations", ()):
        operation = _operation_for_row(row)
        if operation is not None:
            operations.append(operation)
    if not operations:
        raise ValueError("Reviewed apply manifest contains no actionable Rekordbox DB cleanup operations")
    write_json(out_path, _operations_manifest(apply_manifest, operations))
    return out_path


def _require_apply_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("mode") != "dry_run_only":
        raise ValueError("Cleanup apply manifest must be dry_run_only")


def _operation_for_row(row: dict[str, Any]) -> dict[str, Any] | None:
    decision = str(row.get("review_decision") or "")
    if decision in SKIP_DECISIONS:
        return None
    if decision not in ACTIONABLE_DECISIONS:
        raise ValueError(f"Unsupported cleanup review decision for Rekordbox DB apply: {decision}")
    track_id = str(row.get("track_id") or "")
    candidate = str(row.get("candidate_path") or "")
    if not track_id or not candidate:
        raise ValueError("Reviewed cleanup path updates require track_id and candidate_path")
    folder, filename = _split_rekordbox_path(candidate)
    return {
        "operation": "update",
        "table": "djmdContent",
        "values": {"FolderPath": folder, "FileNameL": filename},
        "where": {"ID": track_id},
    }


def _split_rekordbox_path(path: str) -> tuple[str, str]:
    if "/" in path and "\\" not in path:
        item = PurePosixPath(path)
        return str(item.parent), item.name
    item = Path(path)
    return "" if str(item.parent) == "." else str(item.parent), item.name


def _operations_manifest(apply_manifest: Path, operations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": CLEANUP_APPLY_SCHEMA_VERSION,
        "mode": "rekordbox_cleanup_apply_operations",
        "source_apply_manifest": str(apply_manifest),
        "summary": {"update": len(operations)},
        "operations": operations,
    }
