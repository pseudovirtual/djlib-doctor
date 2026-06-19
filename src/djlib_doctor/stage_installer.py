from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from .safety import all_checks_passed, check_app_processes_closed, check_sqlite_sidecars
from .stage_common import require_install_token, require_sha256


def require_stage_token(prefix: str, payload: object, recorded_token: str, confirm_token: str) -> None:
    require_install_token(prefix, payload, recorded_token, confirm_token)


def require_file_hash(path: Path, expected_hash: str, label: str) -> None:
    require_sha256(path, expected_hash, label)


def require_file_hashes(rows: tuple[tuple[Path, str, str], ...] | list[tuple[Path, str, str]]) -> None:
    for path, expected_hash, label in rows:
        require_file_hash(path, expected_hash, label)


def require_no_sqlite_sidecars(db_path: Path, code: str, message: str) -> None:
    if not all_checks_passed(check_sqlite_sidecars(db_path, code=code)):
        raise RuntimeError(message)


def require_app_closed(
    process_lines: tuple[str, ...] | list[str] | None, app_patterns: dict[str, tuple[str, ...]], message: str
) -> None:
    if process_lines is None:
        return
    if not all_checks_passed(check_app_processes_closed(process_lines, app_patterns)):
        raise RuntimeError(message)


def copy_required_backup(source: Path, backup: Path) -> None:
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, backup)
    if not backup.is_file():
        raise RuntimeError(f"Required backup was not created: {backup}")


def backup_and_replace(source: Path, target: Path, backup: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    if existed and not backup.is_file():
        copy_required_backup(target, backup)
    replace_atomically(source, target)
    return {"path": str(target), "backup": str(backup) if existed else "", "existed": existed}


def replace_atomically(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.djlib-doctor-tmp")
    try:
        shutil.copy2(source, temp)
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()


def restore_backups(backups: list[dict[str, Any]]) -> None:
    for item in reversed(backups):
        path = Path(item["path"])
        if item.get("existed"):
            shutil.copy2(Path(item["backup"]), path)
        elif path.exists():
            path.unlink()
