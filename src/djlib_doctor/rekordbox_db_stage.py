from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json
from .rekordbox_cleanup_apply import build_rekordbox_cleanup_operations
from .rekordbox_db_import import build_rekordbox_db_import_operations
from .rekordbox_db_write import apply_rekordbox_operations
from .sqlite_stage import (
    SQLITE_INSTALL_SCHEMA_VERSION,
    SQLITE_STAGE_SCHEMA_VERSION,
    SqliteStage,
    install_sqlite_stage,
)
from .stage_common import install_token, sha256_file
from .stage_installer import require_app_closed, require_no_sqlite_sidecars


def stage_rekordbox_db_operations(live_db: Path, operations_manifest: Path, stage_dir: Path) -> SqliteStage:
    return _stage_rekordbox_db_operations(live_db, operations_manifest, stage_dir)


def stage_rekordbox_db_import(live_db: Path, port_manifest: Path, stage_dir: Path) -> SqliteStage:
    operations = build_rekordbox_db_import_operations(
        live_db, port_manifest, stage_dir / "rekordbox-db-import-operations.json"
    )
    return stage_rekordbox_db_operations(live_db, operations, stage_dir)


def stage_rekordbox_db_apply(live_db: Path, apply_manifest: Path, stage_dir: Path) -> SqliteStage:
    operations = build_rekordbox_cleanup_operations(
        apply_manifest, stage_dir / "rekordbox-cleanup-apply-operations.json"
    )
    return stage_rekordbox_db_operations(live_db, operations, stage_dir)


def install_rekordbox_db_stage(
    stage_dir: Path, live_db: Path, confirm_token: str, process_lines: tuple[str, ...] | list[str] | None = None
) -> dict[str, Any]:
    require_app_closed(
        process_lines, {"rekordbox": ("rekordbox",)}, "Refusing to install while Rekordbox appears to be running"
    )
    return install_sqlite_stage(stage_dir, live_db, confirm_token, label="rekordbox", artifact_prefix="rekordbox-db")


def _stage_rekordbox_db_operations(live_db: Path, operations_manifest: Path, stage_dir: Path) -> SqliteStage:
    require_no_sqlite_sidecars(
        live_db, "rekordbox_sqlite_sidecar_absent", "Refusing to stage Rekordbox DB operations while sidecars exist"
    )
    stage_dir.mkdir(parents=True, exist_ok=True)
    staged_db = stage_dir / live_db.name
    shutil.copy2(live_db, staged_db)
    operations = tuple(read_json(operations_manifest).get("operations", ()))
    apply_rekordbox_operations(staged_db, operations)
    hashes = {"source_db": sha256_file(live_db), "staged_db": sha256_file(staged_db)}
    token = install_token("INSTALL_SQLITE_STAGE", hashes)
    manifest = {
        "schema_version": SQLITE_STAGE_SCHEMA_VERSION,
        "mode": "staged_rekordbox_db_operations",
        "label": "rekordbox",
        "source_db": str(live_db),
        "operations_manifest": str(operations_manifest),
        "staged_db": str(staged_db),
        "operations": len(operations),
        "hashes": hashes,
        "install_token": token,
    }
    stage_manifest_path = stage_dir / "rekordbox-db-stage-manifest.json"
    write_json(stage_manifest_path, manifest)
    return SqliteStage(stage_dir, stage_manifest_path, staged_db, token)


__all__ = [
    "SQLITE_INSTALL_SCHEMA_VERSION",
    "SQLITE_STAGE_SCHEMA_VERSION",
    "SqliteStage",
    "install_rekordbox_db_stage",
    "stage_rekordbox_db_apply",
    "stage_rekordbox_db_import",
    "stage_rekordbox_db_operations",
]
