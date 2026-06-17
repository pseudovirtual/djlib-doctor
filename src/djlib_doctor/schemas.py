from __future__ import annotations

from typing import Any

from .apply_manifest import APPLY_MANIFEST_SCHEMA_VERSION
from .compare import COMPARE_SCHEMA_VERSION
from .config import CONFIG_SCHEMA_VERSION
from .decision_sheet import DECISION_SHEET_FIELDS
from .file_operations import FILE_OPS_INSTALL_SCHEMA_VERSION, FILE_OPS_STAGE_SCHEMA_VERSION
from .fingerprint import SCHEMA_VERSION as FINGERPRINT_SCHEMA_VERSION
from .certify import SCHEMA_VERSION as CERTIFICATION_SCHEMA_VERSION
from .io_utils import render_json
from .plan import PLAN_SCHEMA_VERSION
from .port_serato_rekordbox import REKORDBOX_PORT_SCHEMA_VERSION
from .port_rekordbox_serato import PORT_MANIFEST_SCHEMA_VERSION
from .rekordbox_db_import import IMPORT_SCHEMA_VERSION
from .reviewer import REVIEW_SCHEMA_VERSION
from .rekordbox_db_stage import SQLITE_INSTALL_SCHEMA_VERSION, SQLITE_STAGE_SCHEMA_VERSION
from .serato_audio_tags import SERATO_AUDIO_TAG_INSTALL_SCHEMA_VERSION, SERATO_AUDIO_TAG_STAGE_SCHEMA_VERSION
from .serato_sqlite import SERATO_INSPECTION_SCHEMA_VERSION
from .serato_stage import SERATO_INSTALL_SCHEMA_VERSION, SERATO_STAGE_SCHEMA_VERSION
from .snapshot import SNAPSHOT_SCHEMA_VERSION
from .verify import SCHEMA_VERSION as VERIFY_SCHEMA_VERSION

VERIFY_FIELDS = ("schema_version", "status", "source", "counts", "failures", "warnings", "next_actions")
SNAPSHOT_FIELDS = ("schema_version", "generated_at", "redacted", "command", "source", "artifacts", "verification", "filesystem")
PLAN_FIELDS = ("schema_version", "plan_type", "summary", "actions")
PLAN_ACTION_FIELDS = ("action", "track_id", "artist", "title", "confidence", "human_review_required", "reason", "evidence", "source_path", "candidate_path", "metadata")
PORT_FIELDS = ("schema_version", "mode", "transfer_mode", "scope", "source_platform", "target_platform", "source_playlist", "target_crate_name", "target_crate_filename", "summary", "cue_policy", "namespace_policy", "tracks", "skipped", "warnings", "crates")
AUDIO_PROBE_FIELDS = ("track_id", "artist", "title", "path", "extension", "codec", "sample_rate_hz", "bit_depth", "bit_rate_kbps", "duration_seconds", "probe_ok")
FINGERPRINT_FIELDS = ("schema_version", "path", "size", "sha256", "byte_histogram")
CERTIFICATION_FIELDS = ("schema_version", "passed", "manifest_path", "source_platform", "target_platform", "summary", "issues")


def _json_schema(version: str, fields: tuple[str, ...], **extra: Any) -> dict[str, Any]:
    return {"schema_version": version, "format": "json", "top_level_fields": list(fields), **extra}


SCHEMAS: dict[str, dict[str, Any]] = {
    "verification": _json_schema(VERIFY_SCHEMA_VERSION, VERIFY_FIELDS, status_values=["pass", "fail"]),
    "config": _json_schema(CONFIG_SCHEMA_VERSION, ("schema_version", "primary", "rekordbox_xml", "rekordbox_db", "serato_library_dir", "serato_music_dir", "music_root", "crate_prefix"), primary_values=["rekordbox", "serato"]),
    "snapshot": _json_schema(SNAPSHOT_SCHEMA_VERSION, SNAPSHOT_FIELDS, artifact_paths="relative to snapshot.json unless absolute paths are provided by an older snapshot"),
    "plan": _json_schema(PLAN_SCHEMA_VERSION, PLAN_FIELDS, action_fields=list(PLAN_ACTION_FIELDS)),
    "compare": _json_schema(COMPARE_SCHEMA_VERSION, ("schema_version", "status", "summary", "issues"), issue_codes=["missing_material", "cue_not_covered", "hotcue_regression", "playlist_order_or_entry_diff", "final_bad_path", "final_missing_local_file"]),
    "decision-sheet": {"schema_version": "1.0", "format": "csv", "fields": DECISION_SHEET_FIELDS},
    "review-log": _json_schema(REVIEW_SCHEMA_VERSION, ("schema_version", "source_plan_type", "generated_at", "summary", "decisions"), decision_fields=["review_id", "decision", "notes", "action"]),
    "apply-manifest": _json_schema(APPLY_MANIFEST_SCHEMA_VERSION, ("schema_version", "mode", "source_plan_type", "summary", "safety", "post_apply_verification", "operations"), mode_values=["dry_run_only"]),
    "audio-probe-csv": {"schema_version": "1.0", "format": "csv", "fields": list(AUDIO_PROBE_FIELDS)},
    "fingerprint": _json_schema(FINGERPRINT_SCHEMA_VERSION, FINGERPRINT_FIELDS),
    "fingerprint-comparison": _json_schema(FINGERPRINT_SCHEMA_VERSION, ("schema_version", "comparison_basis", "claims_audio_identity", "classification", "byte_similarity", "left", "right"), classification_values=["exact_duplicate", "byte_similar", "different"]),
    "fingerprint-manifest": _json_schema(FINGERPRINT_SCHEMA_VERSION, ("schema_version", "root", "redacted_paths", "file_count", "files")),
    "certification": _json_schema(CERTIFICATION_SCHEMA_VERSION, CERTIFICATION_FIELDS, severity_values=["info", "warning", "error"]),
    "serato-inspection": _json_schema(SERATO_INSPECTION_SCHEMA_VERSION, ("schema_version", "source", "summary", "schema_fingerprint", "tables", "asset_identity")),
    "port-manifest": _json_schema(PORT_MANIFEST_SCHEMA_VERSION, PORT_FIELDS, summary_fields=["crates", "tracks", "cue_intents", "skipped", "unsupported_tracks", "format_counts", "cue_counts", "warnings"], mode_values=["dry_run_only"]),
    "rekordbox-port-manifest": _json_schema(REKORDBOX_PORT_SCHEMA_VERSION, ("schema_version", "mode", "transfer_mode", "scope", "source_platform", "target_platform", "source_crate", "target_playlist", "summary", "tracks", "skipped"), mode_values=["dry_run_only"]),
    "serato-stage-manifest": _json_schema(SERATO_STAGE_SCHEMA_VERSION, ("schema_version", "mode", "safety", "source_port_manifest", "live_targets", "staged_files", "summary", "crates", "hashes", "source_hashes", "install_token"), mode_values=["staged_serato_install"]),
    "serato-install-report": _json_schema(SERATO_INSTALL_SCHEMA_VERSION, ("schema_version", "passed", "stage_manifest", "backup_dir", "installed_files")),
    "serato-audio-tag-stage-manifest": _json_schema(SERATO_AUDIO_TAG_STAGE_SCHEMA_VERSION, ("schema_version", "mode", "safety", "source_port_manifest", "summary", "tracks", "hashes", "source_hashes", "install_token"), mode_values=["staged_serato_audio_tags"]),
    "serato-audio-tag-install-report": _json_schema(SERATO_AUDIO_TAG_INSTALL_SCHEMA_VERSION, ("schema_version", "passed", "stage_manifest", "backup_dir", "installed")),
    "file-operations-stage-manifest": _json_schema(FILE_OPS_STAGE_SCHEMA_VERSION, ("schema_version", "mode", "source_manifest", "operations", "install_token", "safety"), mode_values=["staged_file_operations"]),
    "file-operations-install-report": _json_schema(FILE_OPS_INSTALL_SCHEMA_VERSION, ("schema_version", "passed", "stage_manifest", "backup_dir", "applied")),
    "rekordbox-db-import-operations": _json_schema(IMPORT_SCHEMA_VERSION, ("schema_version", "mode", "source_port_manifest", "target_table", "summary", "operations"), mode_values=["rekordbox_db_import_operations"]),
    "rekordbox-db-stage-manifest": _json_schema(SQLITE_STAGE_SCHEMA_VERSION, ("schema_version", "mode", "label", "source_db", "operations_manifest", "staged_db", "operations", "hashes", "install_token"), mode_values=["staged_sqlite_operations"]),
    "rekordbox-db-install-report": _json_schema(SQLITE_INSTALL_SCHEMA_VERSION, ("schema_version", "passed", "stage_manifest", "backup", "installed_db")),
}


def schema_names() -> tuple[str, ...]:
    return tuple(sorted(SCHEMAS))


def get_schema(name: str) -> dict[str, Any]:
    try:
        return SCHEMAS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown schema {name!r}. Known schemas: {', '.join(schema_names())}") from exc


def render_schema(name: str | None = None, pretty: bool = False) -> str:
    data = get_schema(name) if name else {"schemas": {schema_name: SCHEMAS[schema_name] for schema_name in schema_names()}}
    return render_json(data, pretty=pretty)
