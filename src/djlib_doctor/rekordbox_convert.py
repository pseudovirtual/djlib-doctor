from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audio_encoding import encode_audio, encoder_delay_ms, require_audio_tools
from .io_utils import read_json, write_json
from .rekordbox_anlz import shift_anlz_beatgrids, shift_anlz_cues
from .safety import all_checks_passed, check_sqlite_sidecars
from .sqlite_utils import quote_identifier, require_integrity
from .stage_common import install_token, sha256_file

CONVERT_STAGE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class RekordboxConvertStage:
    stage_dir: Path
    stage_manifest_path: Path
    staged_db: Path
    install_token: str


def stage_rekordbox_conversion(
    live_db: Path, operations_manifest: Path, stage_dir: Path, cue_shift: str = "auto"
) -> RekordboxConvertStage:
    if cue_shift not in {"auto", "none"}:
        raise ValueError("cue_shift must be 'auto' or 'none'")
    require_audio_tools()
    _check_db_sidecars(live_db)
    stage_dir.mkdir(parents=True, exist_ok=True)
    staged_db = stage_dir / live_db.name
    shutil.copy2(live_db, staged_db)
    operations = read_json(operations_manifest).get("operations", ())
    staged_ops = [
        _stage_conversion(index, op, staged_db, stage_dir, cue_shift) for index, op in enumerate(operations, 1)
    ]
    hashes = {"source_db": sha256_file(live_db), "staged_db": sha256_file(staged_db)}
    token = install_token("INSTALL_REKORDBOX_CONVERT", {"hashes": hashes, "operations": staged_ops})
    manifest_path = stage_dir / "rekordbox-convert-stage-manifest.json"
    write_json(
        manifest_path,
        {
            "schema_version": CONVERT_STAGE_SCHEMA_VERSION,
            "mode": "staged_rekordbox_conversion",
            "source_db": str(live_db),
            "operations_manifest": str(operations_manifest),
            "staged_db": str(staged_db),
            "hashes": hashes,
            "operations": staged_ops,
            "install_token": token,
        },
    )
    return RekordboxConvertStage(stage_dir, manifest_path, staged_db, token)


def _stage_conversion(
    index: int, operation: dict[str, Any], staged_db: Path, stage_dir: Path, cue_shift: str
) -> dict[str, Any]:
    source = Path(operation["source"])
    target = Path(operation["target"])
    staged_audio = stage_dir / "staged-files" / f"OP-{index:04d}-{target.name}"
    staged_audio.parent.mkdir(parents=True, exist_ok=True)
    encode_audio(source, staged_audio, str(operation.get("preset") or "aac-m4a-256"))
    measured_shift_ms = encoder_delay_ms(staged_audio) if staged_audio.suffix.lower() in {".m4a", ".mp4", ".aac"} else 0
    shift_ms = 0 if cue_shift == "none" else measured_shift_ms
    _update_staged_db(staged_db, str(operation["track_id"]), target, shift_ms)
    anlz_entries = [
        _stage_anlz(index, Path(path), stage_dir / "staged-anlz", shift_ms) for path in operation.get("anlz_files", ())
    ]
    return {
        "operation_id": f"OP-{index:04d}",
        "track_id": str(operation["track_id"]),
        "source": str(source),
        "source_sha256": sha256_file(source),
        "target": str(target),
        "staged_audio": str(staged_audio),
        "staged_audio_sha256": sha256_file(staged_audio),
        "preset": str(operation.get("preset") or "aac-m4a-256"),
        "cue_shift": cue_shift,
        "measured_encoder_delay_ms": measured_shift_ms,
        "cue_shift_ms": shift_ms,
        "anlz_files": anlz_entries,
    }


def _stage_anlz(index: int, source: Path, staged_dir: Path, shift_ms: int) -> dict[str, Any]:
    staged = staged_dir / f"OP-{index:04d}-{source.name}"
    shifted = shift_anlz_cues(source, staged, shift_ms)
    shifted_beatgrids = shift_anlz_beatgrids(source, staged, shift_ms)
    return {
        "source": str(source),
        "source_sha256": sha256_file(source),
        "staged": str(staged),
        "staged_sha256": sha256_file(staged),
        "shifted_cues": shifted,
        "shifted_beatgrid_entries": shifted_beatgrids,
    }


def _update_staged_db(db: Path, track_id: str, target: Path, shift_ms: int) -> None:
    conn = sqlite3.connect(db)
    try:
        require_integrity(conn, "before staged Rekordbox conversion")
        folder = "" if str(target.parent) == "." else str(target.parent)
        conn.execute(
            f"UPDATE {quote_identifier('djmdContent')} SET FolderPath = ?, FileNameL = ? WHERE ID = ?",
            (folder, target.name, track_id),
        )
        if shift_ms:
            _shift_cue_rows(conn, track_id, shift_ms)
        require_integrity(conn, "after staged Rekordbox conversion")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _shift_cue_rows(conn: sqlite3.Connection, track_id: str, shift_ms: int) -> None:
    rows = conn.execute(
        f"SELECT ID, InMsec, OutMsec FROM {quote_identifier('djmdCue')} WHERE ContentID = ?",
        (track_id,),
    ).fetchall()
    for cue_id, in_msec, out_msec in rows:
        conn.execute(
            f"UPDATE {quote_identifier('djmdCue')} SET InMsec = ?, OutMsec = ? WHERE ID = ?",
            (
                max(0, int(in_msec or 0) + shift_ms),
                None if out_msec is None else max(0, int(out_msec) + shift_ms),
                cue_id,
            ),
        )


def _check_db_sidecars(live_db: Path) -> None:
    checks = check_sqlite_sidecars(live_db, code="rekordbox_sqlite_sidecar_absent")
    if not all_checks_passed(checks):
        raise RuntimeError("Refusing to stage or install Rekordbox conversion while DB sidecars exist")
