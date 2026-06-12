from __future__ import annotations

import json
from typing import Any

from .apply_manifest import APPLY_MANIFEST_SCHEMA_VERSION
from .compare import COMPARE_SCHEMA_VERSION
from .config import CONFIG_SCHEMA_VERSION
from .decision_sheet import DECISION_SHEET_FIELDS
from .file_operations import FILE_OPS_INSTALL_SCHEMA_VERSION, FILE_OPS_STAGE_SCHEMA_VERSION
from .plan import PLAN_SCHEMA_VERSION
from .port_serato import PORT_MANIFEST_SCHEMA_VERSION
from .port_rekordbox import REKORDBOX_PORT_SCHEMA_VERSION
from .reviewer import REVIEW_SCHEMA_VERSION
from .serato_audio_tags import SERATO_AUDIO_TAG_INSTALL_SCHEMA_VERSION, SERATO_AUDIO_TAG_STAGE_SCHEMA_VERSION
from .serato_sqlite import SERATO_INSPECTION_SCHEMA_VERSION
from .serato_stage import SERATO_INSTALL_SCHEMA_VERSION, SERATO_STAGE_SCHEMA_VERSION
from .sqlite_stage import SQLITE_INSTALL_SCHEMA_VERSION, SQLITE_STAGE_SCHEMA_VERSION
from .snapshot import SNAPSHOT_SCHEMA_VERSION
from .verify import SCHEMA_VERSION as VERIFY_SCHEMA_VERSION


SCHEMAS: dict[str, dict[str, Any]] = {
    "verification": {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "status", "source", "counts", "failures", "warnings", "next_actions"],
        "status_values": ["pass", "fail"],
    },
    "config": {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": [
            "schema_version",
            "rekordbox_xml",
            "serato_library_dir",
            "serato_music_dir",
            "music_root",
            "crate_prefix",
        ],
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
    "rekordbox-port-manifest": {
        "schema_version": REKORDBOX_PORT_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": [
            "schema_version",
            "mode",
            "source_platform",
            "target_platform",
            "source_crate",
            "target_playlist",
            "summary",
            "tracks",
            "skipped",
        ],
        "mode_values": ["dry_run_only"],
    },
    "serato-stage-manifest": {
        "schema_version": SERATO_STAGE_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": [
            "schema_version",
            "mode",
            "safety",
            "source_port_manifest",
            "live_targets",
            "staged_files",
            "summary",
            "crates",
            "hashes",
            "install_token",
        ],
        "mode_values": ["staged_serato_install"],
    },
    "serato-install-report": {
        "schema_version": SERATO_INSTALL_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "passed", "stage_manifest", "backup_dir", "installed_files"],
    },
    "serato-audio-tag-stage-manifest": {
        "schema_version": SERATO_AUDIO_TAG_STAGE_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": [
            "schema_version",
            "mode",
            "safety",
            "source_port_manifest",
            "summary",
            "tracks",
            "hashes",
            "install_token",
        ],
        "mode_values": ["staged_serato_audio_tags"],
    },
    "serato-audio-tag-install-report": {
        "schema_version": SERATO_AUDIO_TAG_INSTALL_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "passed", "stage_manifest", "backup_dir", "installed"],
    },
    "file-operations-stage-manifest": {
        "schema_version": FILE_OPS_STAGE_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "mode", "source_manifest", "operations", "install_token", "safety"],
        "mode_values": ["staged_file_operations"],
    },
    "file-operations-install-report": {
        "schema_version": FILE_OPS_INSTALL_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "passed", "stage_manifest", "backup_dir", "applied"],
    },
    "sqlite-stage-manifest": {
        "schema_version": SQLITE_STAGE_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "mode", "label", "source_db", "operations_manifest", "staged_db", "operations", "hashes", "install_token"],
        "mode_values": ["staged_sqlite_operations"],
    },
    "sqlite-install-report": {
        "schema_version": SQLITE_INSTALL_SCHEMA_VERSION,
        "format": "json",
        "top_level_fields": ["schema_version", "passed", "stage_manifest", "backup", "installed_db"],
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
