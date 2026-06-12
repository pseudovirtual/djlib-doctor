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


def check_app_processes_closed(
    process_lines: list[str] | tuple[str, ...],
    app_patterns: dict[str, tuple[str, ...]],
) -> tuple[SafetyCheck, ...]:
    normalized_lines = tuple(line.lower() for line in process_lines)
    checks = []
    for app_name, patterns in app_patterns.items():
        normalized_patterns = tuple(pattern.lower() for pattern in patterns)
        matches = [
            line
            for line in normalized_lines
            if any(pattern in line for pattern in normalized_patterns)
        ]
        checks.append(
            SafetyCheck(
                code=f"{app_name}_app_closed",
                passed=not matches,
                message=(
                    f"{app_name} appears to be running"
                    if matches
                    else f"{app_name} does not appear to be running"
                ),
            )
        )
    return tuple(checks)


def timestamped_backup_path(source: Path, label: str, now: datetime | None = None) -> Path:
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return source.with_name(f"{source.stem}.{label}.{stamp}{source.suffix}")
