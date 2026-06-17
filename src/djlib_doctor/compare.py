from __future__ import annotations

from collections import Counter
from pathlib import Path

from .compare_models import COMPARE_SCHEMA_VERSION, CompareIssue, CompareReport
from .cues import CueKind
from .locations import LocationKind
from .matching import normalize_text
from .path_hygiene import find_bad_path_marker
from .rekordbox_xml import RekordboxLibrary, Track, parse_rekordbox_xml

CUE_TOLERANCE_SECONDS = 0.11

__all__ = [
    "COMPARE_SCHEMA_VERSION",
    "CompareIssue",
    "CompareReport",
    "compare_exports",
    "write_compare_report",
]


def compare_exports(baseline_xml: Path, final_xml: Path, check_files: bool = False) -> CompareReport:
    baseline = parse_rekordbox_xml(baseline_xml)
    final = parse_rekordbox_xml(final_xml)
    issues: list[CompareIssue] = []
    issues.extend(_material_issues(baseline, final))
    issues.extend(_cue_issues(baseline, final))
    issues.extend(_playlist_issues(baseline, final))
    issues.extend(_final_bad_path_issues(final))
    if check_files:
        issues.extend(_final_missing_file_issues(final))
    return CompareReport(issues=tuple(issues))


def write_compare_report(report: CompareReport, out_path: Path, pretty: bool = True) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.render_json(pretty=pretty) + "\n", encoding="utf-8")


def _material_issues(baseline: RekordboxLibrary, final: RekordboxLibrary) -> list[CompareIssue]:
    baseline_counts = Counter(_track_signature(track) for track in _material_tracks(baseline))
    final_counts = Counter(_track_signature(track) for track in _material_tracks(final))
    issues = []
    for sig, count in sorted(baseline_counts.items()):
        missing = count - final_counts.get(sig, 0)
        if missing <= 0:
            continue
        artist, title = sig
        issues.append(
            CompareIssue(
                code="missing_material",
                message=f"Baseline material track is not represented in final export: {artist} - {title} ({missing} missing)",
                artist=artist,
                title=title,
            )
        )
    return issues


def _cue_issues(baseline: RekordboxLibrary, final: RekordboxLibrary) -> list[CompareIssue]:
    final_by_sig: dict[tuple[str, str], list[Track]] = {}
    for track in _material_tracks(final):
        final_by_sig.setdefault(_track_signature(track), []).append(track)

    issues = []
    for track in _material_tracks(baseline):
        sig = _track_signature(track)
        final_tracks = final_by_sig.get(sig, [])
        if not final_tracks:
            continue
        final_cues = [cue for final_track in final_tracks for cue in final_track.cues]
        for cue in track.cues:
            if not any(abs(cue.start - final_cue.start) <= CUE_TOLERANCE_SECONDS for final_cue in final_cues):
                issues.append(
                    CompareIssue(
                        code="cue_not_covered",
                        message=f"Baseline cue at {cue.start:.3f}s is not covered in final export: {track.artist or ''} - {track.name or ''}",
                        artist=track.artist or "",
                        title=track.name or "",
                    )
                )
        baseline_hotcues = sum(1 for cue in track.cues if cue.kind is CueKind.HOTCUE)
        final_hotcues = max(
            (sum(1 for cue in final_track.cues if cue.kind is CueKind.HOTCUE) for final_track in final_tracks),
            default=0,
        )
        if baseline_hotcues > final_hotcues:
            issues.append(
                CompareIssue(
                    code="hotcue_regression",
                    message=f"Final export has fewer hotcues for material track: {track.artist or ''} - {track.name or ''}",
                    artist=track.artist or "",
                    title=track.name or "",
                )
            )
    return issues


def _playlist_issues(baseline: RekordboxLibrary, final: RekordboxLibrary) -> list[CompareIssue]:
    baseline_tracks = baseline.track_by_id()
    final_tracks = final.track_by_id()
    final_playlists = {playlist.name: playlist for playlist in final.playlists}
    issues = []
    for playlist in baseline.playlists:
        final_playlist = final_playlists.get(playlist.name)
        if final_playlist is None:
            issues.append(
                CompareIssue(
                    code="playlist_order_or_entry_diff",
                    message=f"Playlist missing from final export: {playlist.name}",
                    playlist=playlist.name,
                )
            )
            continue
        baseline_sequence = [
            _track_signature(baseline_tracks[track_id]) for track_id in playlist.entries if track_id in baseline_tracks
        ]
        final_sequence = [
            _track_signature(final_tracks[track_id]) for track_id in final_playlist.entries if track_id in final_tracks
        ]
        if baseline_sequence != final_sequence:
            issues.append(
                CompareIssue(
                    code="playlist_order_or_entry_diff",
                    message=f"Playlist entries or order differ after material projection: {playlist.name}",
                    playlist=playlist.name,
                )
            )
    return issues


def _final_bad_path_issues(final: RekordboxLibrary) -> list[CompareIssue]:
    issues = []
    for track in final.tracks:
        if track.location_kind is not LocationKind.LOCAL_FILE or track.path is None:
            continue
        marker = find_bad_path_marker(str(track.path))
        if not marker:
            continue
        issues.append(
            CompareIssue(
                code="final_bad_path",
                message=f"Final export still references bad/staging folder marker {marker}: {track.artist or ''} - {track.name or ''}",
                artist=track.artist or "",
                title=track.name or "",
                path=str(track.path),
            )
        )
    return issues


def _final_missing_file_issues(final: RekordboxLibrary) -> list[CompareIssue]:
    issues = []
    for track in final.tracks:
        if track.location_kind is not LocationKind.LOCAL_FILE:
            continue
        if track.path is not None and track.path.exists():
            continue
        issues.append(
            CompareIssue(
                code="final_missing_local_file",
                message=f"Final export references a missing local file: {track.artist or ''} - {track.name or ''} :: {track.path or ''}",
                artist=track.artist or "",
                title=track.name or "",
                path=str(track.path or ""),
            )
        )
    return issues


def _material_tracks(library: RekordboxLibrary) -> list[Track]:
    return [track for track in library.tracks if track.location_kind is not LocationKind.STREAMING_PLACEHOLDER]


def _track_signature(track: Track) -> tuple[str, str]:
    return (normalize_text(track.artist), normalize_text(track.name))
