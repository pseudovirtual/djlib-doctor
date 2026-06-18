from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json
from .rekordbox_db_write import update_track_location_and_cues
from .safety import all_checks_passed, check_app_processes_closed, check_sqlite_sidecars
from .stage_common import backup_name, install_token, require_install_token, require_sha256, sha256_file

MOVE_STAGE_SCHEMA_VERSION = "1.0"
MOVE_INSTALL_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class RekordboxMoveStage:
    stage_dir: Path
    stage_manifest_path: Path
    staged_db: Path
    install_token: str


def stage_rekordbox_move(live_db: Path, operations_manifest: Path, stage_dir: Path) -> RekordboxMoveStage:
    _check_db_sidecars(live_db, "stage")
    stage_dir.mkdir(parents=True, exist_ok=True)
    staged_db = stage_dir / live_db.name
    shutil.copy2(live_db, staged_db)
    operations = read_json(operations_manifest).get("operations", ())
    staged_ops = [
        _stage_operation(index, operation, staged_db, stage_dir) for index, operation in enumerate(operations, 1)
    ]
    hashes = {"source_db": sha256_file(live_db), "staged_db": sha256_file(staged_db)}
    token = install_token("INSTALL_REKORDBOX_MOVE", {"hashes": hashes, "operations": staged_ops})
    manifest_path = stage_dir / "rekordbox-move-stage-manifest.json"
    write_json(
        manifest_path,
        {
            "schema_version": MOVE_STAGE_SCHEMA_VERSION,
            "mode": "staged_rekordbox_move",
            "source_db": str(live_db),
            "operations_manifest": str(operations_manifest),
            "staged_db": str(staged_db),
            "hashes": hashes,
            "operations": staged_ops,
            "install_token": token,
        },
    )
    return RekordboxMoveStage(stage_dir, manifest_path, staged_db, token)


def install_rekordbox_move(
    stage_dir: Path,
    live_db: Path,
    confirm_token: str,
    process_lines: tuple[str, ...] | list[str] | None,
) -> dict[str, Any]:
    manifest_path = stage_dir / "rekordbox-move-stage-manifest.json"
    manifest = read_json(manifest_path)
    require_install_token(
        "INSTALL_REKORDBOX_MOVE",
        {"hashes": manifest["hashes"], "operations": manifest["operations"]},
        manifest["install_token"],
        confirm_token,
    )
    _check_processes(process_lines)
    _check_db_sidecars(live_db, "install")
    require_sha256(live_db, manifest["hashes"]["source_db"], "Live Rekordbox DB")
    require_sha256(Path(manifest["staged_db"]), manifest["hashes"]["staged_db"], "Staged Rekordbox DB")
    for operation in manifest["operations"]:
        _verify_operation(operation)
    backup_dir = stage_dir / "rekordbox-move-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups = [_install_db(Path(manifest["staged_db"]), live_db, backup_dir)]
    for operation in manifest["operations"]:
        backups.extend(_install_operation(operation, backup_dir))
    report = {
        "schema_version": MOVE_INSTALL_SCHEMA_VERSION,
        "passed": True,
        "stage_manifest": str(manifest_path),
        "backup_dir": str(backup_dir),
        "backups": backups,
    }
    write_json(stage_dir / "rekordbox-move-install-report.json", report)
    return report


def _stage_operation(index: int, operation: dict[str, Any], staged_db: Path, stage_dir: Path) -> dict[str, Any]:
    source = Path(operation["source"])
    target = Path(operation["target"])
    if source == target:
        raise ValueError("Rekordbox move source and target must differ")
    if not source.is_file():
        raise FileNotFoundError(source)
    staged = stage_dir / "staged-files" / f"OP-{index:04d}-{target.name}"
    staged.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, staged)
    _update_staged_db(staged_db, str(operation["track_id"]), target)
    return {
        "operation_id": f"OP-{index:04d}",
        "track_id": str(operation["track_id"]),
        "source": str(source),
        "source_sha256": sha256_file(source),
        "target": str(target),
        "staged_path": str(staged),
        "staged_sha256": sha256_file(staged),
    }


def _update_staged_db(db: Path, track_id: str, target: Path) -> None:
    update_track_location_and_cues(db, track_id, target, 0, "staged Rekordbox move")


def _install_operation(operation: dict[str, Any], backup_dir: Path) -> list[dict[str, Any]]:
    source = Path(operation["source"])
    target = Path(operation["target"])
    staged = Path(operation["staged_path"])
    backups = [_copy_with_backup(staged, target, backup_dir)]
    backup = backup_dir / backup_name(source)
    shutil.copy2(source, backup)
    backups.append({"path": str(source), "backup": str(backup), "existed": True})
    source.unlink()
    return backups


def _verify_operation(operation: dict[str, Any]) -> None:
    require_sha256(Path(operation["source"]), operation["source_sha256"], "Move source")
    require_sha256(Path(operation["staged_path"]), operation["staged_sha256"], "Staged move file")


def _install_db(staged_db: Path, live_db: Path, backup_dir: Path) -> dict[str, Any]:
    backup = backup_dir / backup_name(live_db)
    shutil.copy2(live_db, backup)
    shutil.copy2(staged_db, live_db)
    return {"path": str(live_db), "backup": str(backup), "kind": "rekordbox_db"}


def _copy_with_backup(source: Path, target: Path, backup_dir: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / backup_name(target)
    existed = target.exists()
    if existed:
        shutil.copy2(target, backup)
    _copy_atomically(source, target)
    return {"path": str(target), "backup": str(backup) if existed else "", "existed": existed}


def _copy_atomically(source: Path, target: Path) -> None:
    temp = target.with_name(f".{target.name}.djlib-doctor-tmp")
    try:
        shutil.copy2(source, temp)
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()


def _check_processes(process_lines: tuple[str, ...] | list[str] | None) -> None:
    if process_lines is None:
        return
    checks = check_app_processes_closed(process_lines, {"rekordbox": ("rekordbox",)})
    if not all_checks_passed(checks):
        raise RuntimeError("Refusing to install while Rekordbox appears to be running")


def _check_db_sidecars(live_db: Path, action: str) -> None:
    checks = check_sqlite_sidecars(live_db, code="rekordbox_sqlite_sidecar_absent")
    if not all_checks_passed(checks):
        raise RuntimeError(f"Refusing to {action} Rekordbox move while DB sidecars exist")
