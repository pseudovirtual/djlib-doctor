from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3
import time

from .io_utils import read_json, write_json
from .safety import all_checks_passed, check_serato_sqlite_sidecars
from .serato_crate import safe_crate_filename, write_serato_crate
from .serato_stage_common import install_token_payload, manifest_crates, stage_hashes
from .serato_stage_install import verify_serato_stage
from .serato_stage_models import SERATO_STAGE_SCHEMA_VERSION, SeratoStageReport
from .serato_stage_sql import current_revision, update_revision, write_crate_to_sqlite
from .sqlite_utils import require_integrity
from .stage_common import install_token, sha256_file


def stage_serato_from_port_manifest(port_manifest_path: Path, live_serato_library_dir: Path, live_serato_music_dir: Path, stage_dir: Path) -> SeratoStageReport:
    crates = manifest_crates(read_json(port_manifest_path))
    if not crates:
        raise ValueError("Port manifest has no crates or tracks to stage")
    live_root = live_serato_library_dir / "root.sqlite"
    if not live_root.is_file():
        raise FileNotFoundError(live_root)
    if not all_checks_passed(check_serato_sqlite_sidecars(live_root)):
        raise RuntimeError("Refusing to stage while Serato SQLite sidecars exist")
    staged_root, stage_subcrates = _copy_stage_roots(live_root, stage_dir)
    crate_paths, per_crate_reports = _write_stage(staged_root, stage_subcrates, crates)
    source_hashes = {"root_sqlite": sha256_file(live_root)}
    hashes = stage_hashes(staged_root, tuple(crate_paths))
    manifest = _stage_manifest(port_manifest_path, live_serato_library_dir, live_serato_music_dir, staged_root, crate_paths, per_crate_reports, hashes, source_hashes)
    manifest["install_token"] = install_token("INSTALL_SERATO_STAGE", install_token_payload(manifest))
    stage_manifest_path = stage_dir / "serato-stage-manifest.json"
    write_json(stage_manifest_path, manifest)
    write_json(stage_dir / "serato-stage-verification.json", verify_serato_stage(stage_dir).to_dict())
    return SeratoStageReport(stage_dir, stage_manifest_path, staged_root, tuple(crate_paths), manifest["install_token"], manifest["summary"])


def _copy_stage_roots(live_root: Path, stage_dir: Path) -> tuple[Path, Path]:
    stage_library = stage_dir / "Library"
    stage_subcrates = stage_dir / "_Serato_" / "Subcrates"
    stage_library.mkdir(parents=True, exist_ok=True)
    stage_subcrates.mkdir(parents=True, exist_ok=True)
    staged_root = stage_library / "root.sqlite"
    shutil.copy2(live_root, staged_root)
    return staged_root, stage_subcrates


def _write_stage(staged_root: Path, stage_subcrates: Path, crates: tuple[dict, ...]) -> tuple[list[Path], list[dict]]:
    conn = sqlite3.connect(staged_root)
    crate_paths = []
    reports = []
    try:
        require_integrity(conn, "before stage write", label="Serato root.sqlite")
        revision = current_revision(conn) + 1
        now = int(time.time())
        update_revision(conn, revision)
        for crate in crates:
            reports.append(_write_crate(conn, crate, stage_subcrates, crate_paths, revision, now))
        require_integrity(conn, "after stage write", label="Serato root.sqlite")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return crate_paths, reports


def _write_crate(conn: sqlite3.Connection, crate: dict, stage_subcrates: Path, crate_paths: list[Path], revision: int, now: int) -> dict:
    crate_name = str(crate["target_crate_name"])
    tracks = tuple(crate.get("tracks", ()))
    crate_path = _unique_crate_path(stage_subcrates, crate_name, crate_paths)
    write_serato_crate(crate_path, tuple(str(track["serato_portable_id"]) for track in tracks))
    created, reused = write_crate_to_sqlite(conn, crate_name, tracks, revision, now)
    crate_paths.append(crate_path)
    return {"source_playlist": crate.get("source_playlist", ""), "target_crate_name": crate_name, "crate_path": str(crate_path), "tracks": len(tracks), "created_assets": created, "reused_assets": reused}


def _stage_manifest(port_manifest_path: Path, live_library: Path, live_music: Path, staged_root: Path, crate_paths: list[Path], reports: list[dict], hashes: dict, source_hashes: dict) -> dict:
    return {
        "schema_version": SERATO_STAGE_SCHEMA_VERSION,
        "mode": "staged_serato_install",
        "safety": {"writes_live_serato_library": False, "writes_audio_tags": False, "requires_install_command": True},
        "source_port_manifest": str(port_manifest_path),
        "live_targets": {"serato_library_dir": str(live_library), "serato_music_dir": str(live_music)},
        "staged_files": {"root_sqlite": str(staged_root), "crates": [str(path) for path in crate_paths]},
        "summary": {"crates": len(crate_paths), "tracks": sum(int(report["tracks"]) for report in reports), "created_assets": sum(int(report["created_assets"]) for report in reports), "reused_assets": sum(int(report["reused_assets"]) for report in reports)},
        "crates": reports,
        "hashes": hashes,
        "source_hashes": source_hashes,
    }


def _unique_crate_path(out_dir: Path, crate_name: str, existing_paths: list[Path]) -> Path:
    base = safe_crate_filename(crate_name)
    candidate = out_dir / f"{base}.crate"
    index = 2
    while candidate in set(existing_paths):
        candidate = out_dir / f"{base} ({index}).crate"
        index += 1
    return candidate
