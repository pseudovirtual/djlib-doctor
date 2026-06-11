from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SafetyCheck:
    code: str
    passed: bool
    message: str


def check_rekordbox_db_sidecars(db_path: Path) -> tuple[SafetyCheck, ...]:
    return check_sqlite_sidecars(db_path, code="rekordbox_db_sidecar_absent")


def check_serato_sqlite_sidecars(sqlite_path: Path) -> tuple[SafetyCheck, ...]:
    return check_sqlite_sidecars(sqlite_path, code="serato_sqlite_sidecar_absent")


def check_sqlite_sidecars(db_path: Path, code: str = "sqlite_sidecar_absent") -> tuple[SafetyCheck, ...]:
    sidecars = (
        db_path.with_name(db_path.name + "-wal"),
        db_path.with_name(db_path.name + "-shm"),
        db_path.with_name(db_path.name + "-journal"),
    )
    checks = []
    for sidecar in sidecars:
        exists = sidecar.exists()
        checks.append(
            SafetyCheck(
                code=code,
                passed=not exists,
                message=f"{sidecar} {'exists' if exists else 'is absent'}",
            )
        )
    return tuple(checks)


def all_checks_passed(checks: tuple[SafetyCheck, ...]) -> bool:
    return all(check.passed for check in checks)


def timestamped_backup_path(source: Path, label: str, now: datetime | None = None) -> Path:
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return source.with_name(f"{source.stem}.{label}.{stamp}{source.suffix}")
