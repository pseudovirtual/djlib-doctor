from __future__ import annotations

from pathlib import Path

from .locations import LocationKind
from .rekordbox_xml import RekordboxLibrary, Track
from .verify_findings import build_findings
from .verify_models import Finding, FindingSeverity, VerificationReport

SCHEMA_VERSION = "1.0"


def verify_library(library: RekordboxLibrary, check_files: bool = True, source_path: str = "") -> VerificationReport:
    local_tracks = [track for track in library.tracks if track.location_kind is LocationKind.LOCAL_FILE]
    streaming_tracks = [track for track in library.tracks if track.location_kind is LocationKind.STREAMING_PLACEHOLDER]
    unknown_tracks = [track for track in library.tracks if track.location_kind is LocationKind.UNKNOWN]
    missing = tuple(track for track in local_tracks if _is_missing(track, check_files))
    all_cues = [cue for track in library.tracks for cue in track.cues]
    return VerificationReport(
        schema_version=SCHEMA_VERSION,
        source_path=source_path,
        check_files=check_files,
        collection_tracks=len(library.tracks),
        playlist_refs=len(library.playlist_refs),
        local_file_tracks=len(local_tracks),
        streaming_placeholders=len(streaming_tracks),
        unknown_location_tracks=len(unknown_tracks),
        missing_local_files=missing,
        cue_count=len(all_cues),
        hotcue_count=sum(1 for cue in all_cues if cue.kind.value == "hotcue"),
        memory_cue_count=sum(1 for cue in all_cues if cue.kind.value == "memory"),
        loop_count=sum(1 for cue in all_cues if cue.cue_type.value == "loop"),
        findings=build_findings(library, missing, unknown_tracks),
    )


def _is_missing(track: Track, check_files: bool) -> bool:
    return check_files and (track.path is None or not Path(track.path).exists())


__all__ = ["SCHEMA_VERSION", "Finding", "FindingSeverity", "VerificationReport", "verify_library"]
