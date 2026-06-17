from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .io_utils import write_json
from .redaction import redact_path
from .rekordbox_xml import parse_rekordbox_xml
from .snapshot_writers import (
    redact_report,
    write_cue_summary,
    write_filesystem_inventory,
    write_missing_files,
    write_playlist_summary,
    write_streaming_placeholders,
    write_track_summary,
)
from .verify import VerificationReport, verify_library

SNAPSHOT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class SnapshotResult:
    out_dir: Path
    snapshot_path: Path
    verification_text_path: Path
    verification_json_path: Path
    missing_files_path: Path
    streaming_placeholders_path: Path
    track_summary_path: Path
    cue_summary_path: Path
    playlist_summary_path: Path
    filesystem_inventory_path: Optional[Path]
    report: VerificationReport


def create_snapshot(
    rekordbox_xml: Path,
    out_dir: Path,
    music_root: Optional[Path] = None,
    check_files: bool = True,
    redact_paths: bool = False,
) -> SnapshotResult:
    library = parse_rekordbox_xml(rekordbox_xml)
    report = verify_library(library, check_files=check_files, source_path=str(rekordbox_xml))
    report_for_output = redact_report(report) if redact_paths else report
    out_dir.mkdir(parents=True, exist_ok=True)

    verification_text_path = out_dir / "verification.txt"
    verification_json_path = out_dir / "verification.json"
    missing_files_path = out_dir / "missing-files.csv"
    streaming_placeholders_path = out_dir / "streaming-placeholders.csv"
    track_summary_path = out_dir / "track-summary.csv"
    cue_summary_path = out_dir / "cue-summary.csv"
    playlist_summary_path = out_dir / "playlist-summary.csv"
    filesystem_inventory_path = out_dir / "filesystem-inventory.csv" if music_root else None
    snapshot_path = out_dir / "snapshot.json"

    verification_text_path.write_text(report_for_output.render_text() + "\n", encoding="utf-8")
    verification_json_path.write_text(report_for_output.render_json(pretty=True) + "\n", encoding="utf-8")
    write_missing_files(missing_files_path, library, report.missing_local_files, redact_paths=redact_paths)
    write_streaming_placeholders(streaming_placeholders_path, library, redact_paths=redact_paths)
    write_track_summary(track_summary_path, library, redact_paths=redact_paths)
    write_cue_summary(cue_summary_path, library)
    write_playlist_summary(playlist_summary_path, library)
    filesystem_summary = None
    if music_root is not None:
        filesystem_summary = write_filesystem_inventory(
            filesystem_inventory_path, music_root, redact_paths=redact_paths
        )

    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "redacted": redact_paths,
        "command": {
            "name": "snapshot",
            "options": {
                "check_files": check_files,
                "music_root_provided": music_root is not None,
                "redact_paths": redact_paths,
            },
        },
        "source": {
            "rekordbox_xml": redact_path(rekordbox_xml) if redact_paths else str(rekordbox_xml),
            "music_root": redact_path(music_root)
            if redact_paths and music_root
            else str(music_root)
            if music_root
            else None,
            "check_files": check_files,
        },
        "artifacts": {
            "verification_text": verification_text_path.name,
            "verification_json": verification_json_path.name,
            "missing_files_csv": missing_files_path.name,
            "streaming_placeholders_csv": streaming_placeholders_path.name,
            "track_summary_csv": track_summary_path.name,
            "cue_summary_csv": cue_summary_path.name,
            "playlist_summary_csv": playlist_summary_path.name,
            "filesystem_inventory_csv": filesystem_inventory_path.name if filesystem_inventory_path else None,
        },
        "verification": report_for_output.to_dict(),
        "filesystem": filesystem_summary,
    }
    write_json(snapshot_path, snapshot)

    return SnapshotResult(
        out_dir=out_dir,
        snapshot_path=snapshot_path,
        verification_text_path=verification_text_path,
        verification_json_path=verification_json_path,
        missing_files_path=missing_files_path,
        streaming_placeholders_path=streaming_placeholders_path,
        track_summary_path=track_summary_path,
        cue_summary_path=cue_summary_path,
        playlist_summary_path=playlist_summary_path,
        filesystem_inventory_path=filesystem_inventory_path,
        report=report_for_output,
    )
