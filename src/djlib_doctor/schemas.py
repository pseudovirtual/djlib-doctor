from __future__ import annotations

import json
from typing import Any

from .apply_manifest import APPLY_MANIFEST_SCHEMA_VERSION
from .compare import COMPARE_SCHEMA_VERSION
from .decision_sheet import DECISION_SHEET_FIELDS
from .plan import PLAN_SCHEMA_VERSION
from .port_serato import PORT_MANIFEST_SCHEMA_VERSION
from .reviewer import REVIEW_SCHEMA_VERSION
from .serato_sqlite import SERATO_INSPECTION_SCHEMA_VERSION
from .snapshot import SNAPSHOT_SCHEMA_VERSION
from .verify import SCHEMA_VERSION as VERIFY_SCHEMA_VERSION


SCHEMAS: dict[str, dict[str, Any]] = {
    "verification": {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "status", "source", "counts", "failures", "warnings", "next_actions"],
        "status_values": ["pass", "fail"],
    },
    "snapshot": {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "generated_at", "redacted", "command", "source", "artifacts", "verification", "filesystem"],
        "artifact_paths": "relative to snapshot.json unless absolute paths are provided by an older snapshot",
    },
    "plan": {
        "schema_version": PLAN_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "plan_type", "summary", "actions"],
        "action_fields": [
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
            "metadata",
        ],
    },
    "compare": {
        "schema_version": COMPARE_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "status", "summary", "issues"],
        "issue_codes": [
            "missing_material",
            "cue_not_covered",
            "hotcue_regression",
            "playlist_order_or_entry_diff",
            "final_bad_path",
            "final_missing_local_file",
        ],
    },
    "decision-sheet": {
        "schema_version": "1.0",
        "format": "csv",
        "fields": DECISION_SHEET_FIELDS,
    },
    "review-log": {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "source_plan_type", "generated_at", "summary", "decisions"],
        "decision_fields": ["review_id", "decision", "notes", "action"],
    },
    "apply-manifest": {
        "schema_version": APPLY_MANIFEST_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": [
            "schema_version",
            "mode",
            "source_plan_type",
            "summary",
            "safety",
            "post_apply_verification",
            "operations",
        ],
        "mode_values": ["dry_run_only"],
    },
    "audio-probe-csv": {
        "schema_version": "1.0",
        "format": "csv",
        "fields": [
            "track_id",
            "artist",
            "title",
            "path",
            "extension",
            "codec",
            "sample_rate_hz",
            "bit_depth",
            "bit_rate_kbps",
            "duration_seconds",
            "probe_ok",
        ],
    },
    "serato-inspection": {
        "schema_version": SERATO_INSPECTION_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "source", "summary", "schema_fingerprint", "tables", "asset_identity"],
    },
    "port-manifest": {
        "schema_version": PORT_MANIFEST_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": [
            "schema_version",
            "mode",
            "source_platform",
            "target_platform",
            "source_playlist",
            "target_crate_name",
            "target_crate_filename",
            "summary",
            "cue_policy",
            "namespace_policy",
            "tracks",
            "skipped",
            "warnings",
            "crates",
        ],
        "summary_fields": [
            "crates",
            "tracks",
            "cue_intents",
            "skipped",
            "unsupported_tracks",
            "format_counts",
            "cue_counts",
            "warnings",
        ],
        "mode_values": ["dry_run_only"],
    },
}


def schema_names() -> tuple[str, ...]:
    return tuple(sorted(SCHEMAS))


def get_schema(name: str) -> dict[str, Any]:
    try:
        return SCHEMAS[name]
    except KeyError as exc:
        known = ", ".join(schema_names())
        raise ValueError(f"Unknown schema {name!r}. Known schemas: {known}") from exc


def render_schema(name: str | None = None, pretty: bool = False) -> str:
    data: Any
    if name:
        data = get_schema(name)
    else:
        data = {"schemas": {schema_name: SCHEMAS[schema_name] for schema_name in schema_names()}}
    if pretty:
        return json.dumps(data, indent=2, sort_keys=True)
    return json.dumps(data, sort_keys=True)
