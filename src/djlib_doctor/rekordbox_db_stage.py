from __future__ import annotations

from pathlib import Path
from typing import Any

from .sqlite_stage import SQLITE_INSTALL_SCHEMA_VERSION, SQLITE_STAGE_SCHEMA_VERSION, SqliteStage, install_sqlite_stage, stage_sqlite_operations


def stage_rekordbox_db_operations(live_db: Path, operations_manifest: Path, stage_dir: Path) -> SqliteStage:
    return stage_sqlite_operations(live_db, operations_manifest, stage_dir, label="rekordbox", artifact_prefix="rekordbox-db")


def install_rekordbox_db_stage(stage_dir: Path, live_db: Path, confirm_token: str) -> dict[str, Any]:
    return install_sqlite_stage(stage_dir, live_db, confirm_token, label="rekordbox", artifact_prefix="rekordbox-db")


__all__ = [
    "SQLITE_INSTALL_SCHEMA_VERSION",
    "SQLITE_STAGE_SCHEMA_VERSION",
    "SqliteStage",
    "install_rekordbox_db_stage",
    "stage_rekordbox_db_operations",
]
