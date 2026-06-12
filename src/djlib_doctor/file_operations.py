from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .io_utils import read_json, write_json
from .stage_common import backup_name, install_token, require_install_token, require_sha256, sha256_file


FILE_OPS_STAGE_SCHEMA_VERSION = "1.0"
FILE_OPS_INSTALL_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class FileOperationsStage:
    stage_dir: Path
    stage_manifest_path: Path
    install_token: str


def stage_file_operations(operations_manifest: Path, stage_dir: Path) -> FileOperationsStage:
    data = read_json(operations_manifest)
    staged_dir = stage_dir / "staged-files"
    staged_dir.mkdir(parents=True, exist_ok=True)
    staged_ops = []
    for index, operation in enumerate(data.get("operations", ()), 1):
        staged_ops.append(_stage_operation(index, operation, staged_dir))
    token = install_token("INSTALL_FILE_OPS", staged_ops)
    stage_manifest = {
        "schema_version": FILE_OPS_STAGE_SCHEMA_VERSION,
        "mode": "staged_file_operations",
        "source_manifest": str(operations_manifest),
        "operations": staged_ops,
        "install_token": token,
        "safety": {"requires_install_command": True, "backs_up_targets": True},
    }
    stage_manifest_path = stage_dir / "file-operations-stage-manifest.json"
    write_json(stage_manifest_path, stage_manifest)
    return FileOperationsStage(stage_dir, stage_manifest_path, token)


def apply_file_operations_stage(stage_dir: Path, confirm_token: str) -> dict[str, Any]:
    manifest_path = stage_dir / "file-operations-stage-manifest.json"
    manifest = read_json(manifest_path)
    require_install_token("INSTALL_FILE_OPS", manifest["operations"], manifest["install_token"], confirm_token)
    backup_dir = stage_dir / "file-operation-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    applied = []
    for operation in manifest["operations"]:
        applied.append(_apply_operation(operation, backup_dir))
    report = {
        "schema_version": FILE_OPS_INSTALL_SCHEMA_VERSION,
        "passed": True,
        "stage_manifest": str(manifest_path),
        "backup_dir": str(backup_dir),
        "applied": applied,
    }
    report_path = stage_dir / "file-operations-install-report.json"
    write_json(report_path, report)
    return report


def _stage_operation(index: int, operation: dict[str, Any], staged_dir: Path) -> dict[str, Any]:
    kind = operation["operation"]
    if kind in {"copy", "move"}:
        source = Path(operation["source"])
        if not source.is_file():
            raise FileNotFoundError(source)
        staged = staged_dir / f"OP-{index:04d}-{source.name}"
        shutil.copy2(source, staged)
        return {
            "operation_id": f"OP-{index:04d}",
            "operation": kind,
            "source": str(source),
            "source_sha256": sha256_file(source),
            "target": str(Path(operation["target"])),
            "staged_path": str(staged),
            "staged_sha256": sha256_file(staged),
        }
    if kind == "delete":
        source = Path(operation["source"])
        if not source.is_file():
            raise FileNotFoundError(source)
        return {
            "operation_id": f"OP-{index:04d}",
            "operation": kind,
            "source": str(source),
            "source_sha256": sha256_file(source),
        }
    if kind == "convert":
        source = Path(operation["source"])
        target = Path(operation["target"])
        staged = staged_dir / f"OP-{index:04d}-{target.name}"
        subprocess.run(["ffmpeg", "-y", "-i", str(source), str(staged)], check=True, capture_output=True)
        return {
            "operation_id": f"OP-{index:04d}",
            "operation": kind,
            "source": str(source),
            "source_sha256": sha256_file(source),
            "target": str(target),
            "staged_path": str(staged),
            "staged_sha256": sha256_file(staged),
        }
    raise ValueError(f"Unsupported file operation: {kind}")


def _apply_operation(operation: dict[str, Any], backup_dir: Path) -> dict[str, Any]:
    kind = operation["operation"]
    source = Path(operation["source"])
    if kind in {"copy", "move", "convert"}:
        target = Path(operation["target"])
        staged = Path(operation["staged_path"])
        require_sha256(staged, operation["staged_sha256"], "Staged file")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, backup_dir / backup_name(target))
        shutil.copy2(staged, target)
        if kind == "move":
            require_sha256(source, operation["source_sha256"], "Move source")
            shutil.copy2(source, backup_dir / backup_name(source))
            source.unlink()
        return {"operation_id": operation["operation_id"], "operation": kind, "target": str(target)}
    if kind == "delete":
        require_sha256(source, operation["source_sha256"], "Delete source")
        shutil.copy2(source, backup_dir / backup_name(source))
        source.unlink()
        return {"operation_id": operation["operation_id"], "operation": kind, "source": str(source)}
    raise ValueError(f"Unsupported file operation: {kind}")
