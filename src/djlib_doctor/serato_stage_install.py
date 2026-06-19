from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json
from .serato_stage_common import file_hash_check, install_token_payload, installed_file_record
from .serato_stage_models import SERATO_INSTALL_SCHEMA_VERSION, SeratoInstallReport, SeratoVerificationReport
from .stage_installer import (
    copy_required_backup,
    require_app_closed,
    require_file_hash,
    require_no_sqlite_sidecars,
    require_stage_token,
)


def verify_serato_stage(stage_dir: Path) -> SeratoVerificationReport:
    manifest = read_json(stage_dir / "serato-stage-manifest.json")
    root = Path(manifest["staged_files"]["root_sqlite"])
    checks = [file_hash_check("root_sqlite_hash", root, manifest["hashes"]["root_sqlite"])]
    checks.extend(
        file_hash_check("crate_hash", Path(path), hash_value)
        for path, hash_value in manifest["hashes"]["crates"].items()
    )
    checks.append(_sqlite_integrity_check(root))
    return SeratoVerificationReport(passed=all(bool(check["passed"]) for check in checks), checks=tuple(checks))


def install_serato_stage(
    stage_dir: Path,
    live_serato_library_dir: Path,
    live_serato_music_dir: Path,
    confirm_token: str,
    process_lines: tuple[str, ...] | list[str] | None = None,
) -> SeratoInstallReport:
    manifest = read_json(stage_dir / "serato-stage-manifest.json")
    require_stage_token(
        "INSTALL_SERATO_STAGE", install_token_payload(manifest), manifest["install_token"], confirm_token
    )
    if not verify_serato_stage(stage_dir).passed:
        raise RuntimeError("Refusing to install because staged verification failed")
    live_root = live_serato_library_dir / "root.sqlite"
    require_file_hash(live_root, manifest["source_hashes"]["root_sqlite"], "Live Serato root.sqlite source")
    require_no_sqlite_sidecars(
        live_root, "serato_sqlite_sidecar_absent", "Refusing to install while Serato SQLite sidecars exist"
    )
    require_app_closed(
        process_lines, {"serato": ("Serato DJ", "serato")}, "Refusing to install while Serato appears to be running"
    )
    return _install_files(stage_dir, live_root, live_serato_music_dir, manifest)


def _install_files(
    stage_dir: Path, live_root: Path, live_serato_music_dir: Path, manifest: dict[str, Any]
) -> SeratoInstallReport:
    staged_root = Path(manifest["staged_files"]["root_sqlite"])
    staged_crates = tuple(Path(path) for path in manifest["staged_files"]["crates"])
    backup_dir = stage_dir / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_library = backup_dir / "Library"
    backup_subcrates = backup_dir / "_Serato_" / "Subcrates"
    backup_library.mkdir(parents=True, exist_ok=True)
    backup_subcrates.mkdir(parents=True, exist_ok=True)
    _copy_required_backup(live_root, backup_library / "root.sqlite")
    live_subcrates = live_serato_music_dir / "Subcrates"
    live_subcrates.mkdir(parents=True, exist_ok=True)
    for staged_crate in staged_crates:
        live_crate = live_subcrates / staged_crate.name
        if live_crate.exists():
            _copy_required_backup(live_crate, backup_subcrates / live_crate.name)
    installed_files = _copy_installs(staged_root, live_root, staged_crates, live_subcrates)
    report_path = stage_dir / "serato-install-report.json"
    passed = all(record["source_sha256"] == record["target_sha256"] for record in installed_files)
    write_json(
        report_path,
        {
            "schema_version": SERATO_INSTALL_SCHEMA_VERSION,
            "passed": passed,
            "stage_manifest": str(stage_dir / "serato-stage-manifest.json"),
            "backup_dir": str(backup_dir),
            "installed_files": installed_files,
        },
    )
    if not passed:
        raise RuntimeError("Installed file hash verification failed")
    return SeratoInstallReport(True, report_path, backup_dir, tuple(installed_files))


def _copy_required_backup(source: Path, backup: Path) -> None:
    copy_required_backup(source, backup)


def _copy_installs(
    staged_root: Path, live_root: Path, staged_crates: tuple[Path, ...], live_subcrates: Path
) -> list[dict[str, str]]:
    installed_files = []
    shutil.copy2(staged_root, live_root)
    installed_files.append(installed_file_record(staged_root, live_root))
    for staged_crate in staged_crates:
        live_crate = live_subcrates / staged_crate.name
        shutil.copy2(staged_crate, live_crate)
        installed_files.append(installed_file_record(staged_crate, live_crate))
    return installed_files


def _sqlite_integrity_check(root: Path) -> dict[str, Any]:
    if not root.is_file():
        return {"code": "sqlite_integrity", "passed": False, "message": "missing staged root.sqlite"}
    conn = sqlite3.connect(root)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()
    return {"code": "sqlite_integrity", "passed": integrity == "ok", "message": str(integrity)}
