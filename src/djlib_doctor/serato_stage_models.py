from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
