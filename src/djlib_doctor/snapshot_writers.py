from __future__ import annotations

from dataclasses import replace
import csv
from pathlib import Path
from typing import Any, Optional

from .audio import iter_audio_files
from .cues import CueKind, CueType
from .locations import LocationKind
from .redaction import redact_path, redact_text_path, redact_uri_or_path
from .rekordbox_xml import RekordboxLibrary, Track
from .verify import VerificationReport


def write_missing_files(path: Path, library: RekordboxLibrary, tracks: tuple[Track, ...], redact_paths: bool = False) -> None:
    playlist_refs = playlist_refs_by_track(library)
    rows = [{"track_id": track.track_id, "artist": track.artist or "", "title": track.name or "", "kind": track.format or "", "cue_count": len(track.cues), "playlist_count": len(playlist_refs.get(track.track_id, [])), "playlists": " | ".join(playlist_refs.get(track.track_id, [])), "path": display_path(track.path, redact_paths)} for track in tracks]
    write_csv(path, ["track_id", "artist", "title", "kind", "cue_count", "playlist_count", "playlists", "path"], rows)


def write_streaming_placeholders(path: Path, library: RekordboxLibrary, redact_paths: bool = False) -> None:
    rows = [{"track_id": track.track_id, "artist": track.artist or "", "title": track.name or "", "kind": track.format or "", "location": redact_uri_or_path(track.location) if redact_paths else track.location or ""} for track in library.tracks if track.location_kind is LocationKind.STREAMING_PLACEHOLDER]
    write_csv(path, ["track_id", "artist", "title", "kind", "location"], rows)


def write_track_summary(path: Path, library: RekordboxLibrary, redact_paths: bool = False) -> None:
    playlist_refs = playlist_refs_by_track(library)
    rows = []
    for track in library.tracks:
        rows.append({"track_id": track.track_id, "artist": track.artist or "", "title": track.name or "", "kind": track.format or "", "location_kind": track.location_kind.value, "path": display_path(track.path, redact_paths), "local_exists": "yes" if _local_exists(track) else "no", "cue_count": len(track.cues), "hotcue_count": sum(1 for cue in track.cues if cue.kind is CueKind.HOTCUE), "loop_count": sum(1 for cue in track.cues if cue.cue_type is CueType.LOOP), "playlist_count": len(playlist_refs.get(track.track_id, [])), "playlists": " | ".join(playlist_refs.get(track.track_id, []))})
    write_csv(path, ["track_id", "artist", "title", "kind", "location_kind", "path", "local_exists", "cue_count", "hotcue_count", "loop_count", "playlist_count", "playlists"], rows)


def write_cue_summary(path: Path, library: RekordboxLibrary) -> None:
    rows = [{"track_id": track.track_id, "artist": track.artist or "", "title": track.name or "", "cue_kind": cue.kind.value, "cue_type": cue.cue_type.value, "slot": "" if cue.slot is None else cue.slot, "hotcue_label": cue.hotcue_label or "", "start": f"{cue.start:.3f}", "end": "" if cue.end is None else f"{cue.end:.3f}", "name": cue.name or ""} for track in library.tracks for cue in track.cues]
    write_csv(path, ["track_id", "artist", "title", "cue_kind", "cue_type", "slot", "hotcue_label", "start", "end", "name"], rows)


def write_playlist_summary(path: Path, library: RekordboxLibrary) -> None:
    track_ids = {track.track_id for track in library.tracks}
    rows = [{"playlist": playlist.name, "entries": len(playlist.entries), "missing_collection_refs": len([track_id for track_id in playlist.entries if track_id not in track_ids]), "missing_track_ids": " | ".join(track_id for track_id in playlist.entries if track_id not in track_ids)} for playlist in library.playlists]
    write_csv(path, ["playlist", "entries", "missing_collection_refs", "missing_track_ids"], rows)


def playlist_refs_by_track(library: RekordboxLibrary) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for ref in library.playlist_refs:
        out.setdefault(ref.key, []).append(ref.playlist)
    return out


def write_filesystem_inventory(path: Optional[Path], music_root: Path, redact_paths: bool = False) -> dict[str, Any]:
    if path is None:
        return {"music_root": display_path(music_root, redact_paths), "audio_files": 0, "total_bytes": 0}
    rows = []
    total_bytes = 0
    for audio_file in iter_audio_files(music_root):
        size = audio_file.stat().st_size
        total_bytes += size
        rows.append({"path": display_path(audio_file, redact_paths), "extension": audio_file.suffix.lower(), "size_bytes": size})
    write_csv(path, ["path", "extension", "size_bytes"], rows)
    return {"music_root": display_path(music_root, redact_paths), "audio_files": len(rows), "total_bytes": total_bytes}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def display_path(path: Optional[Path], redact_paths: bool) -> str:
    return "" if path is None else redact_path(path) if redact_paths else str(path)


def redact_report(report: VerificationReport) -> VerificationReport:
    missing = tuple(replace(track, location=redact_uri_or_path(track.location), path=Path(redact_path(track.path)) if track.path else None) for track in report.missing_local_files)
    findings = [replace(finding, path=redact_path(finding.path) if finding.path else "", message=redact_text_path(finding.message, finding.path) if finding.path else finding.message) for finding in report.findings]
    return replace(report, source_path=redact_path(report.source_path), missing_local_files=missing, findings=tuple(findings))


def _local_exists(track: Track) -> bool:
    return bool(track.path and track.path.exists()) if track.location_kind is LocationKind.LOCAL_FILE else False
