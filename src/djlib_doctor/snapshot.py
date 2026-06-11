from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
from typing import Any, Optional

from .audio import iter_audio_files
from .cues import CueKind, CueType
from .locations import LocationKind
from .redaction import redact_path, redact_text_path, redact_uri_or_path
from .rekordbox_xml import RekordboxLibrary, Track, parse_rekordbox_xml
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
    report_for_output = _redact_report(report) if redact_paths else report
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
    _write_missing_files(missing_files_path, library, report.missing_local_files, redact_paths=redact_paths)
    _write_streaming_placeholders(streaming_placeholders_path, library, redact_paths=redact_paths)
    _write_track_summary(track_summary_path, library, redact_paths=redact_paths)
    _write_cue_summary(cue_summary_path, library)
    _write_playlist_summary(playlist_summary_path, library)
    filesystem_summary = None
    if music_root is not None:
        filesystem_summary = _write_filesystem_inventory(filesystem_inventory_path, music_root, redact_paths=redact_paths)

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
            "music_root": redact_path(music_root) if redact_paths and music_root else str(music_root) if music_root else None,
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
    snapshot_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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


def _write_missing_files(path: Path, library: RekordboxLibrary, tracks: tuple[Track, ...], redact_paths: bool = False) -> None:
    playlist_refs = _playlist_refs_by_track(library)
    _write_csv(
        path,
        ["track_id", "artist", "title", "kind", "cue_count", "playlist_count", "playlists", "path"],
        [
            {
                "track_id": track.track_id,
                "artist": track.artist or "",
                "title": track.name or "",
                "kind": track.format or "",
                "cue_count": len(track.cues),
                "playlist_count": len(playlist_refs.get(track.track_id, [])),
                "playlists": " | ".join(playlist_refs.get(track.track_id, [])),
                "path": _display_path(track.path, redact_paths),
            }
            for track in tracks
        ],
    )


def _write_streaming_placeholders(path: Path, library: RekordboxLibrary, redact_paths: bool = False) -> None:
    rows = []
    for track in library.tracks:
        if track.location_kind is not LocationKind.STREAMING_PLACEHOLDER:
            continue
        rows.append(
            {
                "track_id": track.track_id,
                "artist": track.artist or "",
                "title": track.name or "",
                "kind": track.format or "",
                "location": redact_uri_or_path(track.location) if redact_paths else track.location or "",
            }
        )
    _write_csv(path, ["track_id", "artist", "title", "kind", "location"], rows)


def _write_track_summary(path: Path, library: RekordboxLibrary, redact_paths: bool = False) -> None:
    playlist_refs = _playlist_refs_by_track(library)
    rows = []
    for track in library.tracks:
        hotcue_count = sum(1 for cue in track.cues if cue.kind is CueKind.HOTCUE)
        loop_count = sum(1 for cue in track.cues if cue.cue_type is CueType.LOOP)
        local_exists = bool(track.path and track.path.exists()) if track.location_kind is LocationKind.LOCAL_FILE else False
        rows.append(
            {
                "track_id": track.track_id,
                "artist": track.artist or "",
                "title": track.name or "",
                "kind": track.format or "",
                "location_kind": track.location_kind.value,
                "path": _display_path(track.path, redact_paths),
                "local_exists": "yes" if local_exists else "no",
                "cue_count": len(track.cues),
                "hotcue_count": hotcue_count,
                "loop_count": loop_count,
                "playlist_count": len(playlist_refs.get(track.track_id, [])),
                "playlists": " | ".join(playlist_refs.get(track.track_id, [])),
            }
        )
    _write_csv(
        path,
        [
            "track_id",
            "artist",
            "title",
            "kind",
            "location_kind",
            "path",
            "local_exists",
            "cue_count",
            "hotcue_count",
            "loop_count",
            "playlist_count",
            "playlists",
        ],
        rows,
    )


def _write_cue_summary(path: Path, library: RekordboxLibrary) -> None:
    rows = []
    for track in library.tracks:
        for cue in track.cues:
            rows.append(
                {
                    "track_id": track.track_id,
                    "artist": track.artist or "",
                    "title": track.name or "",
                    "cue_kind": cue.kind.value,
                    "cue_type": cue.cue_type.value,
                    "slot": "" if cue.slot is None else cue.slot,
                    "hotcue_label": cue.hotcue_label or "",
                    "start": f"{cue.start:.3f}",
                    "end": "" if cue.end is None else f"{cue.end:.3f}",
                    "name": cue.name or "",
                }
            )
    _write_csv(
        path,
        ["track_id", "artist", "title", "cue_kind", "cue_type", "slot", "hotcue_label", "start", "end", "name"],
        rows,
    )


def _write_playlist_summary(path: Path, library: RekordboxLibrary) -> None:
    track_ids = {track.track_id for track in library.tracks}
    rows = []
    for playlist in library.playlists:
        missing = [track_id for track_id in playlist.entries if track_id not in track_ids]
        rows.append(
            {
                "playlist": playlist.name,
                "entries": len(playlist.entries),
                "missing_collection_refs": len(missing),
                "missing_track_ids": " | ".join(missing),
            }
        )
    _write_csv(path, ["playlist", "entries", "missing_collection_refs", "missing_track_ids"], rows)


def _playlist_refs_by_track(library: RekordboxLibrary) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for ref in library.playlist_refs:
        out.setdefault(ref.key, []).append(ref.playlist)
    return out


def _write_filesystem_inventory(path: Optional[Path], music_root: Path, redact_paths: bool = False) -> dict[str, Any]:
    if path is None:
        return {"music_root": _display_path(music_root, redact_paths), "audio_files": 0, "total_bytes": 0}
    rows = []
    total_bytes = 0
    for audio_file in iter_audio_files(music_root):
        size = audio_file.stat().st_size
        total_bytes += size
        rows.append(
            {
                "path": _display_path(audio_file, redact_paths),
                "extension": audio_file.suffix.lower(),
                "size_bytes": size,
            }
        )
    _write_csv(path, ["path", "extension", "size_bytes"], rows)
    return {
        "music_root": _display_path(music_root, redact_paths),
        "audio_files": len(rows),
        "total_bytes": total_bytes,
    }


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _display_path(path: Optional[Path], redact_paths: bool) -> str:
    if path is None:
        return ""
    return redact_path(path) if redact_paths else str(path)


def _redact_report(report: VerificationReport) -> VerificationReport:
    missing = tuple(
        replace(
            track,
            location=redact_uri_or_path(track.location),
            path=Path(redact_path(track.path)) if track.path else None,
        )
        for track in report.missing_local_files
    )
    findings = []
    for finding in report.findings:
        redacted_path = redact_path(finding.path) if finding.path else ""
        findings.append(
            replace(
                finding,
                path=redacted_path,
                message=redact_text_path(finding.message, finding.path) if finding.path else finding.message,
            )
        )
    return replace(
        report,
        source_path=redact_path(report.source_path),
        missing_local_files=missing,
        findings=tuple(findings),
    )
