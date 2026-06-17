from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .rekordbox_db_stage import install_rekordbox_db_stage, stage_rekordbox_db_import
from .serato_stage import install_serato_stage, stage_serato_from_port_manifest
from .sync_common import required_path
from .sync_planner import SyncPlanResult, plan_sync


@dataclass(frozen=True)
class SyncRunResult:
    plan: SyncPlanResult
    stage_manifest: Path
    install_report: Path


def run_sync(
    config: dict[str, Any],
    out_dir: Path,
    install_token: str | None = None,
    process_lines: tuple[str, ...] = (),
    **plan_kwargs: Any,
) -> SyncRunResult:
    plan = plan_sync(config, out_dir, **plan_kwargs)
    return install_sync_plan(config, out_dir, plan, install_token, process_lines)


def install_sync_plan(
    config: dict[str, Any],
    out_dir: Path,
    plan: SyncPlanResult,
    install_token: str | None = None,
    process_lines: tuple[str, ...] = (),
) -> SyncRunResult:
    if not plan.certification.passed:
        raise RuntimeError("Refusing to sync because certification did not pass")
    if plan.direction == "rb-to-serato":
        return _run_rekordbox_to_serato(config, out_dir, plan, install_token, process_lines)
    if plan.direction == "serato-to-rb":
        return _run_serato_to_rekordbox(config, out_dir, plan, install_token, process_lines)
    raise ValueError(f"Unknown sync direction: {plan.direction}")


def _run_rekordbox_to_serato(
    config: dict[str, Any],
    out_dir: Path,
    plan: SyncPlanResult,
    install_token: str | None,
    process_lines: tuple[str, ...],
) -> SyncRunResult:
    library = required_path(config, "serato_library_dir")
    music = required_path(config, "serato_music_dir")
    stage = stage_serato_from_port_manifest(plan.port_manifest, library, music, out_dir / "serato-stage")
    token = install_token or stage.install_token
    report = install_serato_stage(stage.stage_dir, library, music, token, process_lines)
    return SyncRunResult(plan, stage.stage_manifest_path, report.report_path)


def _run_serato_to_rekordbox(
    config: dict[str, Any],
    out_dir: Path,
    plan: SyncPlanResult,
    install_token: str | None,
    process_lines: tuple[str, ...],
) -> SyncRunResult:
    db = required_path(config, "rekordbox_db")
    stage = stage_rekordbox_db_import(db, plan.port_manifest, out_dir / "rekordbox-stage")
    token = install_token or stage.install_token
    install_rekordbox_db_stage(stage.stage_dir, db, token, process_lines)
    return SyncRunResult(plan, stage.stage_manifest_path, stage.stage_dir / "rekordbox-db-install-report.json")
