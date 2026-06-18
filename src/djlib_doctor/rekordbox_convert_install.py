from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json
from .safety import all_checks_passed, check_app_processes_closed, check_sqlite_sidecars
from .stage_common import backup_name, require_install_token, require_sha256

CONVERT_INSTALL_SCHEMA_VERSION = "1.0"


def install_rekordbox_conversion(
    stage_dir: Path,
    live_db: Path,
    confirm_token: str,
    process_lines: tuple[str, ...] | list[str] | None,
) -> dict[str, Any]:
    manifest_path = stage_dir / "rekordbox-convert-stage-manifest.json"
    manifest = read_json(manifest_path)
    require_install_token(
        "INSTALL_REKORDBOX_CONVERT",
        {"hashes": manifest["hashes"], "operations": manifest["operations"]},
        manifest["install_token"],
        confirm_token,
    )
    _check_processes(process_lines)
    _check_db_sidecars(live_db)
    require_sha256(live_db, manifest["hashes"]["source_db"], "Live Rekordbox DB")
    require_sha256(Path(manifest["staged_db"]), manifest["hashes"]["staged_db"], "Staged Rekordbox DB")
    backup_dir = stage_dir / "rekordbox-convert-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups = [_install_db(Path(manifest["staged_db"]), live_db, backup_dir)]
    for operation in manifest["operations"]:
        backups.extend(_install_operation(operation, backup_dir))
    report = {
        "schema_version": CONVERT_INSTALL_SCHEMA_VERSION,
        "passed": True,
        "stage_manifest": str(manifest_path),
        "backup_dir": str(backup_dir),
        "backups": backups,
    }
    write_json(stage_dir / "rekordbox-convert-install-report.json", report)
    return report


def _check_processes(process_lines: tuple[str, ...] | list[str] | None) -> None:
    if process_lines is None:
        return
    checks = check_app_processes_closed(process_lines, {"rekordbox": ("rekordbox",)})
    if not all_checks_passed(checks):
        raise RuntimeError("Refusing to install while Rekordbox appears to be running")


def _check_db_sidecars(live_db: Path) -> None:
    checks = check_sqlite_sidecars(live_db, code="rekordbox_sqlite_sidecar_absent")
    if not all_checks_passed(checks):
        raise RuntimeError("Refusing to install Rekordbox conversion while DB sidecars exist")


def _install_db(staged_db: Path, live_db: Path, backup_dir: Path) -> dict[str, Any]:
    backup = backup_dir / backup_name(live_db)
    shutil.copy2(live_db, backup)
    shutil.copy2(staged_db, live_db)
    return {"path": str(live_db), "backup": str(backup), "kind": "rekordbox_db"}


def _install_operation(operation: dict[str, Any], backup_dir: Path) -> list[dict[str, Any]]:
    source = Path(operation["source"])
    target = Path(operation["target"])
    staged_audio = Path(operation["staged_audio"])
    require_sha256(source, operation["source_sha256"], "Conversion source audio")
    require_sha256(staged_audio, operation["staged_audio_sha256"], "Staged converted audio")
    backups = [_copy_with_backup(staged_audio, target, backup_dir)]
    for row in operation.get("anlz_files", ()):
        source_anlz = Path(row["source"])
        staged_anlz = Path(row["staged"])
        require_sha256(source_anlz, row["source_sha256"], "Source ANLZ")
        require_sha256(staged_anlz, row["staged_sha256"], "Staged ANLZ")
        backups.append(_copy_with_backup(staged_anlz, source_anlz, backup_dir))
    return backups


def _copy_with_backup(source: Path, target: Path, backup_dir: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / backup_name(target)
    existed = target.exists()
    if existed:
        shutil.copy2(target, backup)
    shutil.copy2(source, target)
    return {"path": str(target), "backup": str(backup) if existed else "", "existed": existed}
