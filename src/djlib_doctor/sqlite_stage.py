from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any

from .safety import all_checks_passed, check_sqlite_sidecars
from .stage_common import install_token, sha256_file


SQLITE_STAGE_SCHEMA_VERSION = "1.0"
SQLITE_INSTALL_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SqliteStage:
    stage_dir: Path
    stage_manifest_path: Path
    staged_db: Path
    install_token: str


def stage_sqlite_operations(live_db: Path, operations_manifest: Path, stage_dir: Path, label: str = "sqlite") -> SqliteStage:
    sidecar_checks = check_sqlite_sidecars(live_db, code=f"{label}_sqlite_sidecar_absent")
    if not all_checks_passed(sidecar_checks):
        raise RuntimeError("Refusing to stage SQLite operations while sidecars exist")
    stage_dir.mkdir(parents=True, exist_ok=True)
    staged_db = stage_dir / live_db.name
    shutil.copy2(live_db, staged_db)
    operations = json.loads(operations_manifest.read_text(encoding="utf-8")).get("operations", ())
    conn = sqlite3.connect(staged_db)
    try:
        _require_integrity(conn, "before staged SQLite operations")
        for operation in operations:
            _apply_sqlite_operation(conn, operation)
        _require_integrity(conn, "after staged SQLite operations")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    hashes = {"staged_db": sha256_file(staged_db)}
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
    stage_manifest_path = stage_dir / f"{label}-sqlite-stage-manifest.json"
    stage_manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return SqliteStage(stage_dir, stage_manifest_path, staged_db, token)


def install_sqlite_stage(stage_dir: Path, live_db: Path, confirm_token: str, label: str = "sqlite") -> dict[str, Any]:
    manifest_path = stage_dir / f"{label}-sqlite-stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if confirm_token != manifest["install_token"]:
        raise ValueError("Confirmation token does not match staged SQLite token")
    staged_db = Path(manifest["staged_db"])
    if sha256_file(staged_db) != manifest["hashes"]["staged_db"]:
        raise RuntimeError("Staged SQLite hash mismatch")
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
    (stage_dir / f"{label}-sqlite-install-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise RuntimeError("Installed SQLite hash verification failed")
    return report


def _apply_sqlite_operation(conn: sqlite3.Connection, operation: dict[str, Any]) -> None:
    kind = operation["operation"]
    table = _quote_identifier(operation["table"])
    if kind == "update":
        values = operation["values"]
        where = operation["where"]
        assignments = ", ".join(f"{_quote_identifier(column)} = ?" for column in values)
        predicates = " AND ".join(f"{_quote_identifier(column)} = ?" for column in where)
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE {predicates}",
            tuple(values.values()) + tuple(where.values()),
        )
        return
    if kind == "insert":
        values = operation["values"]
        columns = ", ".join(_quote_identifier(column) for column in values)
        placeholders = ", ".join("?" for _ in values)
        conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))
        return
    if kind == "delete":
        where = operation["where"]
        predicates = " AND ".join(f"{_quote_identifier(column)} = ?" for column in where)
        conn.execute(f"DELETE FROM {table} WHERE {predicates}", tuple(where.values()))
        return
    raise ValueError(f"Unsupported SQLite operation: {kind}")


def _require_integrity(conn: sqlite3.Connection, phase: str) -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed {phase}: {integrity}")


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
