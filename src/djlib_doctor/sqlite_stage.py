from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import sqlite3
from typing import Any

from .io_utils import read_json, write_json
from .safety import all_checks_passed, check_sqlite_sidecars
from .sqlite_utils import quote_identifier, require_integrity
from .stage_common import install_token, require_install_token, require_sha256, sha256_file


SQLITE_STAGE_SCHEMA_VERSION = "1.0"
SQLITE_INSTALL_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SqliteStage:
    stage_dir: Path
    stage_manifest_path: Path
    staged_db: Path
    install_token: str


def stage_sqlite_operations(live_db: Path, operations_manifest: Path, stage_dir: Path, label: str = "sqlite", artifact_prefix: str | None = None) -> SqliteStage:
    sidecar_checks = check_sqlite_sidecars(live_db, code=f"{label}_sqlite_sidecar_absent")
    if not all_checks_passed(sidecar_checks):
        raise RuntimeError("Refusing to stage SQLite operations while sidecars exist")
    stage_dir.mkdir(parents=True, exist_ok=True)
    staged_db = stage_dir / live_db.name
    shutil.copy2(live_db, staged_db)
    operations = read_json(operations_manifest).get("operations", ())
    conn = sqlite3.connect(staged_db)
    try:
        require_integrity(conn, "before staged SQLite operations")
        for operation in operations:
            _apply_sqlite_operation(conn, operation)
        require_integrity(conn, "after staged SQLite operations")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    hashes = {"source_db": sha256_file(live_db), "staged_db": sha256_file(staged_db)}
    token = install_token("INSTALL_SQLITE_STAGE", hashes)
    manifest = {
        "schema_version": SQLITE_STAGE_SCHEMA_VERSION,
        "mode": "staged_sqlite_operations",
        "label": label,
        "source_db": str(live_db),
        "operations_manifest": str(operations_manifest),
        "staged_db": str(staged_db),
        "operations": len(tuple(operations)),
        "hashes": hashes,
        "install_token": token,
    }
    stage_manifest_path = stage_dir / f"{artifact_prefix or f'{label}-sqlite'}-stage-manifest.json"
    write_json(stage_manifest_path, manifest)
    return SqliteStage(stage_dir, stage_manifest_path, staged_db, token)


def install_sqlite_stage(stage_dir: Path, live_db: Path, confirm_token: str, label: str = "sqlite", artifact_prefix: str | None = None) -> dict[str, Any]:
    output_prefix = artifact_prefix or f"{label}-sqlite"
    manifest_path = stage_dir / f"{output_prefix}-stage-manifest.json"
    manifest = read_json(manifest_path)
    require_install_token("INSTALL_SQLITE_STAGE", manifest["hashes"], manifest["install_token"], confirm_token)
    staged_db = Path(manifest["staged_db"])
    require_sha256(staged_db, manifest["hashes"]["staged_db"], "Staged SQLite")
    require_sha256(live_db, manifest["hashes"]["source_db"], "Live SQLite source")
    sidecar_checks = check_sqlite_sidecars(live_db, code=f"{label}_sqlite_sidecar_absent")
    if not all_checks_passed(sidecar_checks):
        raise RuntimeError("Refusing to install SQLite stage while sidecars exist")
    backup_dir = stage_dir / "sqlite-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / live_db.name
    shutil.copy2(live_db, backup)
    shutil.copy2(staged_db, live_db)
    passed = sha256_file(live_db) == sha256_file(staged_db)
    report = {
        "schema_version": SQLITE_INSTALL_SCHEMA_VERSION,
        "passed": passed,
        "stage_manifest": str(manifest_path),
        "backup": str(backup),
        "installed_db": str(live_db),
    }
    write_json(stage_dir / f"{output_prefix}-install-report.json", report)
    if not passed:
        raise RuntimeError("Installed SQLite hash verification failed")
    return report


def _apply_sqlite_operation(conn: sqlite3.Connection, operation: dict[str, Any]) -> None:
    kind = operation["operation"]
    table = quote_identifier(operation["table"])
    if kind == "update":
        values = operation["values"]
        where = operation["where"]
        assignments = ", ".join(f"{quote_identifier(column)} = ?" for column in values)
        predicates = " AND ".join(f"{quote_identifier(column)} = ?" for column in where)
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE {predicates}",
            tuple(values.values()) + tuple(where.values()),
        )
        return
    if kind == "insert":
        values = operation["values"]
        columns = ", ".join(quote_identifier(column) for column in values)
        placeholders = ", ".join("?" for _ in values)
        conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))
        return
    if kind == "delete":
        where = operation["where"]
        predicates = " AND ".join(f"{quote_identifier(column)} = ?" for column in where)
        conn.execute(f"DELETE FROM {table} WHERE {predicates}", tuple(where.values()))
        return
    raise ValueError(f"Unsupported SQLite operation: {kind}")
