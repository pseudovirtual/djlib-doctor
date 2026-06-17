from __future__ import annotations

from .cues import CueType
from .rekordbox_xml import RekordboxLibrary, Track
from .verify_models import Finding, FindingSeverity


def build_findings(
    library: RekordboxLibrary, missing_local_files: tuple[Track, ...], unknown_tracks: list[Track]
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    track_ids = [track.track_id for track in library.tracks]
    track_id_set = set(track_ids)
    findings.extend(_missing_file_findings(missing_local_files))
    findings.extend(_duplicate_id_findings(track_ids))
    findings.extend(_missing_playlist_ref_findings(library, track_id_set))
    findings.extend(_unknown_location_findings(unknown_tracks))
    findings.extend(_unknown_cue_findings(library))
    return tuple(findings)


def _missing_file_findings(tracks: tuple[Track, ...]) -> list[Finding]:
    return [
        Finding(
            "missing_local_file",
            FindingSeverity.FAILURE,
            f"Missing local file for TrackID {track.track_id}: {track.artist or ''} - {track.name or ''} :: {track.path}",
            track.track_id,
            path=str(track.path or ""),
        )
        for track in tracks
    ]


def _duplicate_id_findings(track_ids: list[str]) -> list[Finding]:
    return [
        Finding(
            "duplicate_track_id", FindingSeverity.FAILURE, f"Duplicate collection TrackID found: {track_id}", track_id
        )
        for track_id in sorted({track_id for track_id in track_ids if track_ids.count(track_id) > 1 and track_id})
    ]


def _missing_playlist_ref_findings(library: RekordboxLibrary, track_id_set: set[str]) -> list[Finding]:
    return [
        Finding(
            "missing_playlist_track",
            FindingSeverity.FAILURE,
            f"Playlist reference points at missing collection TrackID {ref.key}: {ref.playlist or '(unknown playlist)'}",
            ref.key,
            ref.playlist,
        )
        for ref in library.playlist_refs
        if ref.key not in track_id_set
    ]


def _unknown_location_findings(tracks: list[Track]) -> list[Finding]:
    return [
        Finding(
            "unknown_location",
            FindingSeverity.WARNING,
            f"Unknown location kind for TrackID {track.track_id}: {track.location or '(empty location)'}",
            track.track_id,
        )
        for track in tracks
    ]


def _unknown_cue_findings(library: RekordboxLibrary) -> list[Finding]:
    return [
        Finding(
            "unknown_cue_type",
            FindingSeverity.WARNING,
            f"Unknown cue type on TrackID {track.track_id} at {cue.start:.3f}s",
            track.track_id,
        )
        for track in library.tracks
        for cue in track.cues
        if cue.cue_type is CueType.UNKNOWN
    ]
