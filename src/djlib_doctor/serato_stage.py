from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import time
from typing import Any

from .safety import all_checks_passed, check_app_processes_closed, check_serato_sqlite_sidecars
from .serato_crate import safe_crate_filename, write_serato_crate
from .stage_common import install_token, require_install_token, require_sha256, sha256_file


SERATO_STAGE_SCHEMA_VERSION = "1.0"
SERATO_INSTALL_SCHEMA_VERSION = "1.0"
SERATO_LIBRARY_SPACE_ID = 2
SERATO_LIBRARY_ROOT_CONTAINER_ID = 3


@dataclass(frozen=True)
class SeratoStageReport:
    stage_dir: Path
    stage_manifest_path: Path
    staged_root_sqlite: Path
    crate_paths: tuple[Path, ...]
    install_token: str
    summary: dict[str, Any]


@dataclass(frozen=True)
class SeratoVerificationReport:
    passed: bool
    checks: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "checks": list(self.checks)}


@dataclass(frozen=True)
class SeratoInstallReport:
    passed: bool
    report_path: Path
    backup_dir: Path
    installed_files: tuple[dict[str, str], ...]


def stage_serato_from_port_manifest(
    port_manifest_path: Path,
    live_serato_library_dir: Path,
    live_serato_music_dir: Path,
    stage_dir: Path,
) -> SeratoStageReport:
    manifest = json.loads(port_manifest_path.read_text(encoding="utf-8"))
    crates = _manifest_crates(manifest)
    if not crates:
        raise ValueError("Port manifest has no crates or tracks to stage")

    live_root = live_serato_library_dir / "root.sqlite"
    if not live_root.is_file():
        raise FileNotFoundError(live_root)
    sidecar_checks = check_serato_sqlite_sidecars(live_root)
    if not all_checks_passed(sidecar_checks):
        raise RuntimeError("Refusing to stage while Serato SQLite sidecars exist")

    stage_library = stage_dir / "Library"
    stage_subcrates = stage_dir / "_Serato_" / "Subcrates"
    stage_library.mkdir(parents=True, exist_ok=True)
    stage_subcrates.mkdir(parents=True, exist_ok=True)
    staged_root = stage_library / "root.sqlite"
    shutil.copy2(live_root, staged_root)

    conn = sqlite3.connect(staged_root)
    crate_paths = []
    per_crate_reports = []
    try:
        _require_integrity(conn, "before stage write")
        current_revision = _current_revision(conn)
        revision = current_revision + 1
        now = int(time.time())
        _update_revision(conn, revision)
        for crate in crates:
            crate_name = str(crate["target_crate_name"])
            tracks = tuple(crate.get("tracks", ()))
            crate_path = _unique_crate_path(stage_subcrates, crate_name, crate_paths)
            write_serato_crate(crate_path, tuple(str(track["serato_portable_id"]) for track in tracks))
            created, reused = _write_crate_to_sqlite(conn, crate_name, tracks, revision, now)
            crate_paths.append(crate_path)
            per_crate_reports.append(
                {
                    "source_playlist": crate.get("source_playlist", ""),
                    "target_crate_name": crate_name,
                    "crate_path": str(crate_path),
                    "tracks": len(tracks),
                    "created_assets": created,
                    "reused_assets": reused,
                }
            )
        _require_integrity(conn, "after stage write")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    source_hashes = {"root_sqlite": sha256_file(live_root)}
    stage_hashes = _stage_hashes(staged_root, tuple(crate_paths))
    token = install_token("INSTALL_SERATO_STAGE", _install_token_payload(stage_hashes, source_hashes))
    stage_manifest = {
        "schema_version": SERATO_STAGE_SCHEMA_VERSION,
        "mode": "staged_serato_install",
        "safety": {
            "writes_live_serato_library": False,
            "writes_audio_tags": False,
            "requires_install_command": True,
        },
        "source_port_manifest": str(port_manifest_path),
        "live_targets": {
            "serato_library_dir": str(live_serato_library_dir),
            "serato_music_dir": str(live_serato_music_dir),
        },
        "staged_files": {
            "root_sqlite": str(staged_root),
            "crates": [str(path) for path in crate_paths],
        },
        "summary": {
            "crates": len(crate_paths),
            "tracks": sum(int(report["tracks"]) for report in per_crate_reports),
            "created_assets": sum(int(report["created_assets"]) for report in per_crate_reports),
            "reused_assets": sum(int(report["reused_assets"]) for report in per_crate_reports),
        },
        "crates": per_crate_reports,
        "hashes": stage_hashes,
        "source_hashes": source_hashes,
        "install_token": token,
    }
    stage_manifest_path = stage_dir / "serato-stage-manifest.json"
    stage_manifest_path.write_text(json.dumps(stage_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verification = verify_serato_stage(stage_dir)
    (stage_dir / "serato-stage-verification.json").write_text(
        json.dumps(verification.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return SeratoStageReport(
        stage_dir=stage_dir,
        stage_manifest_path=stage_manifest_path,
        staged_root_sqlite=staged_root,
        crate_paths=tuple(crate_paths),
        install_token=token,
        summary=stage_manifest["summary"],
    )


def verify_serato_stage(stage_dir: Path) -> SeratoVerificationReport:
    manifest_path = stage_dir / "serato-stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = []
    root = Path(manifest["staged_files"]["root_sqlite"])
    checks.append(_file_hash_check("root_sqlite_hash", root, manifest["hashes"]["root_sqlite"]))
    for crate_path, expected_hash in manifest["hashes"]["crates"].items():
        checks.append(_file_hash_check("crate_hash", Path(crate_path), expected_hash))
    if root.is_file():
        conn = sqlite3.connect(root)
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            conn.close()
        checks.append({"code": "sqlite_integrity", "passed": integrity == "ok", "message": str(integrity)})
    else:
        checks.append({"code": "sqlite_integrity", "passed": False, "message": "missing staged root.sqlite"})
    return SeratoVerificationReport(passed=all(bool(check["passed"]) for check in checks), checks=tuple(checks))


def install_serato_stage(
    stage_dir: Path,
    live_serato_library_dir: Path,
    live_serato_music_dir: Path,
    confirm_token: str,
    process_lines: tuple[str, ...] | list[str] | None = None,
) -> SeratoInstallReport:
    manifest = json.loads((stage_dir / "serato-stage-manifest.json").read_text(encoding="utf-8"))
    require_install_token(
        "INSTALL_SERATO_STAGE",
        _install_token_payload(manifest["hashes"], manifest["source_hashes"]),
        manifest["install_token"],
        confirm_token,
    )
    stage_verification = verify_serato_stage(stage_dir)
    if not stage_verification.passed:
        raise RuntimeError("Refusing to install because staged verification failed")

    live_root = live_serato_library_dir / "root.sqlite"
    require_sha256(live_root, manifest["source_hashes"]["root_sqlite"], "Live Serato root.sqlite source")
    sidecar_checks = check_serato_sqlite_sidecars(live_root)
    if not all_checks_passed(sidecar_checks):
        raise RuntimeError("Refusing to install while Serato SQLite sidecars exist")

    if process_lines is not None:
        process_checks = check_app_processes_closed(process_lines, {"serato": ("Serato DJ", "serato")})
        if not all_checks_passed(process_checks):
            raise RuntimeError("Refusing to install while Serato appears to be running")

    staged_root = Path(manifest["staged_files"]["root_sqlite"])
    staged_crates = tuple(Path(path) for path in manifest["staged_files"]["crates"])
    backup_dir = stage_dir / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_library = backup_dir / "Library"
    backup_subcrates = backup_dir / "_Serato_" / "Subcrates"
    backup_library.mkdir(parents=True, exist_ok=True)
    backup_subcrates.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live_root, backup_library / "root.sqlite")

    live_subcrates = live_serato_music_dir / "Subcrates"
    live_subcrates.mkdir(parents=True, exist_ok=True)
    for staged_crate in staged_crates:
        live_crate = live_subcrates / staged_crate.name
        if live_crate.exists():
            shutil.copy2(live_crate, backup_subcrates / live_crate.name)

    installed_files = []
    shutil.copy2(staged_root, live_root)
    installed_files.append(_installed_file_record(staged_root, live_root))
    for staged_crate in staged_crates:
        live_crate = live_subcrates / staged_crate.name
        shutil.copy2(staged_crate, live_crate)
        installed_files.append(_installed_file_record(staged_crate, live_crate))

    passed = all(record["source_sha256"] == record["target_sha256"] for record in installed_files)
    report = {
        "schema_version": SERATO_INSTALL_SCHEMA_VERSION,
        "passed": passed,
        "stage_manifest": str(stage_dir / "serato-stage-manifest.json"),
        "backup_dir": str(backup_dir),
        "installed_files": installed_files,
    }
    report_path = stage_dir / "serato-install-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        raise RuntimeError("Installed file hash verification failed")
    return SeratoInstallReport(
        passed=True,
        report_path=report_path,
        backup_dir=backup_dir,
        installed_files=tuple(installed_files),
    )


def _manifest_crates(manifest: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if "crates" in manifest:
        return tuple(manifest["crates"])
    return (manifest,)


def _write_crate_to_sqlite(
    conn: sqlite3.Connection,
    crate_name: str,
    tracks: tuple[dict[str, Any], ...],
    revision: int,
    now: int,
) -> tuple[int, int]:
    container_id = _upsert_container(conn, crate_name, revision, now)
    conn.execute("DELETE FROM container_asset WHERE container_id = ?", (container_id,))
    created = 0
    reused = 0
    for index, track in enumerate(tracks, 1):
        asset_id, was_created = _upsert_asset(conn, track, revision, now)
        created += 1 if was_created else 0
        reused += 0 if was_created else 1
        space_asset_id = _upsert_space_asset(conn, asset_id)
        _insert_container_asset(conn, container_id, space_asset_id, index, revision, now)
    return created, reused


def _upsert_container(conn: sqlite3.Connection, crate_name: str, revision: int, now: int) -> int:
    _require_columns(conn, "container", ("id", "name", "parent_id", "type", "list_order"))
    existing = conn.execute(
        "SELECT id FROM container WHERE parent_id = ? AND name = ? COLLATE NOCASE AND type = 1",
        (SERATO_LIBRARY_ROOT_CONTAINER_ID, crate_name),
    ).fetchone()
    if existing:
        container_id = int(existing[0])
        _dynamic_update(conn, "container", {"revision": revision}, "id = ?", (container_id,))
        return container_id
    next_order = conn.execute(
        "SELECT COALESCE(MAX(list_order), 0) + 1 FROM container WHERE parent_id = ?",
        (SERATO_LIBRARY_ROOT_CONTAINER_ID,),
    ).fetchone()[0]
    values = {
        "revision": revision,
        "parent_id": SERATO_LIBRARY_ROOT_CONTAINER_ID,
        "name": crate_name,
        "type": 1,
        "list_order": next_order,
        "space_id": SERATO_LIBRARY_SPACE_ID,
        "time_added": now,
        "expanded": 0,
        "portable_id": "",
    }
    return _dynamic_insert(conn, "container", values)


def _upsert_asset(conn: sqlite3.Connection, track: dict[str, Any], revision: int, now: int) -> tuple[int, bool]:
    _require_columns(conn, "asset", ("id", "portable_id"))
    portable_id = str(track["serato_portable_id"])
    existing = conn.execute("SELECT id FROM asset WHERE portable_id = ? COLLATE NOCASE", (portable_id,)).fetchone()
    values = _asset_values(track, revision, now)
    if existing:
        asset_id = int(existing[0])
        _dynamic_update(conn, "asset", values, "id = ?", (asset_id,))
        return asset_id, False
    return _dynamic_insert(conn, "asset", values), True


def _asset_values(track: dict[str, Any], revision: int, now: int) -> dict[str, Any]:
    path = Path(str(track.get("path", "")))
    file_size = path.stat().st_size if path.exists() else 0
    return {
        "revision": revision,
        "portable_id": str(track["serato_portable_id"]),
        "file_name": path.name,
        "file_size": file_size,
        "type": "audio",
        "format": path.suffix.lower().lstrip("."),
        "artist": track.get("artist", ""),
        "comments": "",
        "name": track.get("title", ""),
        "album": "",
        "genre": "",
        "key": "",
        "bpm": None,
        "length_ms": None,
        "time_added": now,
        "time_modified": now,
        "analysis_flags": 0,
        "architectures": 0,
    }


def _upsert_space_asset(conn: sqlite3.Connection, asset_id: int) -> int:
    _require_columns(conn, "space_asset", ("id", "asset_id", "space_id"))
    existing = conn.execute(
        "SELECT id FROM space_asset WHERE asset_id = ? AND space_id = ?",
        (asset_id, SERATO_LIBRARY_SPACE_ID),
    ).fetchone()
    if existing:
        return int(existing[0])
    return _dynamic_insert(conn, "space_asset", {"id": asset_id, "asset_id": asset_id, "space_id": SERATO_LIBRARY_SPACE_ID})


def _insert_container_asset(
    conn: sqlite3.Connection,
    container_id: int,
    space_asset_id: int,
    list_order: int,
    revision: int,
    now: int,
) -> None:
    _require_columns(conn, "container_asset", ("container_id", "space_asset_id"))
    _dynamic_insert(
        conn,
        "container_asset",
        {
            "revision": revision,
            "container_id": container_id,
            "space_asset_id": space_asset_id,
            "list_order": list_order,
            "time_added": now,
        },
    )


def _current_revision(conn: sqlite3.Connection) -> int:
    _require_columns(conn, "serato", ("revision",))
    return int(conn.execute("SELECT revision FROM serato").fetchone()[0])


def _update_revision(conn: sqlite3.Connection, revision: int) -> None:
    conn.execute("UPDATE serato SET revision = ?", (revision,))


def _require_integrity(conn: sqlite3.Connection, phase: str) -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"Serato root.sqlite integrity check failed {phase}: {integrity}")


def _require_columns(conn: sqlite3.Connection, table: str, columns: tuple[str, ...]) -> None:
    existing = set(_table_columns(conn, table))
    missing = [column for column in columns if column not in existing]
    if missing:
        raise ValueError(f"Serato table {table!r} is missing required columns: {', '.join(missing)}")


def _table_columns(conn: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row[1] for row in conn.execute(f"PRAGMA table_info({_quote_identifier(table)})"))


def _dynamic_insert(conn: sqlite3.Connection, table: str, values: dict[str, Any]) -> int:
    columns = tuple(column for column in values if column in _table_columns(conn, table))
    quoted_columns = ", ".join(_quote_identifier(column) for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT INTO {_quote_identifier(table)} ({quoted_columns}) VALUES ({placeholders})",
        tuple(values[column] for column in columns),
    )
    return int(cursor.lastrowid)


def _dynamic_update(
    conn: sqlite3.Connection,
    table: str,
    values: dict[str, Any],
    where_sql: str,
    where_args: tuple[Any, ...],
) -> None:
    columns = tuple(column for column in values if column in _table_columns(conn, table))
    if not columns:
        return
    assignments = ", ".join(f"{_quote_identifier(column)} = ?" for column in columns)
    conn.execute(
        f"UPDATE {_quote_identifier(table)} SET {assignments} WHERE {where_sql}",
        tuple(values[column] for column in columns) + where_args,
    )


def _stage_hashes(root: Path, crate_paths: tuple[Path, ...]) -> dict[str, Any]:
    return {
        "root_sqlite": sha256_file(root),
        "crates": {str(path): sha256_file(path) for path in crate_paths},
    }


def _install_token_payload(stage_hashes: dict[str, Any], source_hashes: dict[str, str]) -> dict[str, Any]:
    return {"hashes": stage_hashes, "source_hashes": source_hashes}


def _file_hash_check(code: str, path: Path, expected_hash: str) -> dict[str, Any]:
    if not path.is_file():
        return {"code": code, "passed": False, "message": f"missing file: {path}"}
    actual = sha256_file(path)
    return {"code": code, "passed": actual == expected_hash, "message": str(path)}


def _installed_file_record(source: Path, target: Path) -> dict[str, str]:
    return {
        "source": str(source),
        "target": str(target),
        "source_sha256": sha256_file(source),
        "target_sha256": sha256_file(target),
    }


def _unique_crate_path(out_dir: Path, crate_name: str, existing_paths: list[Path]) -> Path:
    base = safe_crate_filename(crate_name)
    candidate = out_dir / f"{base}.crate"
    index = 2
    existing = set(existing_paths)
    while candidate in existing:
        candidate = out_dir / f"{base} ({index}).crate"
        index += 1
    return candidate


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
