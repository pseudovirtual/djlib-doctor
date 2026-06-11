from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any

from .cues import CueType
from .locations import LocationKind
from .rekordbox_xml import RekordboxLibrary, Track


SCHEMA_VERSION = "1.0"


class FindingSeverity(str, Enum):
    FAILURE = "failure"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: FindingSeverity
    message: str
    track_id: str = ""
    playlist: str = ""
    path: str = ""

    def to_dict(self) -> dict[str, str]:
        data = {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.track_id:
            data["track_id"] = self.track_id
        if self.playlist:
            data["playlist"] = self.playlist
        if self.path:
            data["path"] = self.path
        return data


@dataclass(frozen=True)
class VerificationReport:
    schema_version: str
    source_path: str
    check_files: bool
    collection_tracks: int
    playlist_refs: int
    local_file_tracks: int
    streaming_placeholders: int
    unknown_location_tracks: int
    missing_local_files: tuple[Track, ...]
    cue_count: int
    hotcue_count: int
    memory_cue_count: int
    loop_count: int
    findings: tuple[Finding, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def failures(self) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if finding.severity is FindingSeverity.FAILURE)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if finding.severity is FindingSeverity.WARNING)

    @property
    def next_actions(self) -> tuple[str, ...]:
        finding_codes = {finding.code for finding in self.findings}
        actions = []
        if "missing_local_file" in finding_codes:
            actions.append("Run `djlib-doctor snapshot` and then `djlib-doctor plan missing-files` to review replacement candidates.")
        if "duplicate_track_id" in finding_codes:
            actions.append("Run `djlib-doctor snapshot` and then `djlib-doctor plan duplicates` to choose cue-safe survivor records.")
        if "missing_playlist_track" in finding_codes:
            actions.append("Inspect playlist references before removing or rebuilding playlists.")
        if "unknown_location" in finding_codes:
            actions.append("Review unknown locations; djlib-doctor will not guess whether they are safe local files or placeholders.")
        if "unknown_cue_type" in finding_codes:
            actions.append("Review unknown cue types before migrating or comparing cue data.")
        if not actions and self.passed:
            actions.append("Create a snapshot before planning any cleanup or comparing this export to another export.")
        return tuple(actions)

    def render_text(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"djlib-doctor verification: {status}",
            f"Source: {self.source_path or '(in-memory library)'}",
            f"File existence check: {'on' if self.check_files else 'off'}",
            f"Collection tracks: {self.collection_tracks}",
            f"Playlist references: {self.playlist_refs}",
            f"Local file-backed tracks: {self.local_file_tracks}",
            f"Streaming placeholders: {self.streaming_placeholders}",
            f"Unknown location tracks: {self.unknown_location_tracks}",
            f"Missing local files: {len(self.missing_local_files)}",
            f"Cues: {self.cue_count} ({self.hotcue_count} hotcue, {self.memory_cue_count} memory, {self.loop_count} loop)",
            f"Failures: {len(self.failures)}",
            f"Warnings: {len(self.warnings)}",
        ]
        if self.failures:
            lines.append("")
            lines.append("Failures:")
            lines.extend(f"- {finding.message}" for finding in self.failures)
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {finding.message}" for finding in self.warnings)
        if self.next_actions:
            lines.append("")
            lines.append("Suggested next actions:")
            lines.extend(f"- {action}" for action in self.next_actions)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": "pass" if self.passed else "fail",
            "source": {
                "type": "rekordbox_xml",
                "path": self.source_path,
                "check_files": self.check_files,
            },
            "counts": {
                "collection_tracks": self.collection_tracks,
                "playlist_references": self.playlist_refs,
                "local_file_tracks": self.local_file_tracks,
                "streaming_placeholders": self.streaming_placeholders,
                "unknown_location_tracks": self.unknown_location_tracks,
                "missing_local_files": len(self.missing_local_files),
                "cues": self.cue_count,
                "hotcues": self.hotcue_count,
                "memory_cues": self.memory_cue_count,
                "loops": self.loop_count,
                "failures": len(self.failures),
                "warnings": len(self.warnings),
            },
            "failures": [finding.to_dict() for finding in self.failures],
            "warnings": [finding.to_dict() for finding in self.warnings],
            "next_actions": list(self.next_actions),
        }

    def render_json(self, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(self.to_dict(), indent=2, sort_keys=True)
        return json.dumps(self.to_dict(), sort_keys=True)


def verify_library(library: RekordboxLibrary, check_files: bool = True, source_path: str = "") -> VerificationReport:
    local_tracks = [track for track in library.tracks if track.location_kind is LocationKind.LOCAL_FILE]
    streaming_tracks = [track for track in library.tracks if track.location_kind is LocationKind.STREAMING_PLACEHOLDER]
    unknown_tracks = [track for track in library.tracks if track.location_kind is LocationKind.UNKNOWN]
    missing = tuple(track for track in local_tracks if _is_missing(track, check_files))
    all_cues = [cue for track in library.tracks for cue in track.cues]
    findings = _build_findings(library, missing, unknown_tracks)

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
        findings=findings,
    )


def _is_missing(track: Track, check_files: bool) -> bool:
    if not check_files:
        return False
    return track.path is None or not Path(track.path).exists()


def _build_findings(
    library: RekordboxLibrary,
    missing_local_files: tuple[Track, ...],
    unknown_tracks: list[Track],
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    track_ids = [track.track_id for track in library.tracks]
    track_id_set = set(track_ids)
    duplicate_track_ids = sorted({track_id for track_id in track_ids if track_ids.count(track_id) > 1 and track_id})

    for track in missing_local_files:
        findings.append(
            Finding(
                code="missing_local_file",
                severity=FindingSeverity.FAILURE,
                message=f"Missing local file for TrackID {track.track_id}: {track.artist or ''} - {track.name or ''} :: {track.path}",
                track_id=track.track_id,
                path=str(track.path or ""),
            )
        )

    for duplicate_track_id in duplicate_track_ids:
        findings.append(
            Finding(
                code="duplicate_track_id",
                severity=FindingSeverity.FAILURE,
                message=f"Duplicate collection TrackID found: {duplicate_track_id}",
                track_id=duplicate_track_id,
            )
        )

    for ref in library.playlist_refs:
        if ref.key not in track_id_set:
            findings.append(
                Finding(
                    code="missing_playlist_track",
                    severity=FindingSeverity.FAILURE,
                    message=f"Playlist reference points at missing collection TrackID {ref.key}: {ref.playlist or '(unknown playlist)'}",
                    track_id=ref.key,
                    playlist=ref.playlist,
                )
            )

    for track in unknown_tracks:
        findings.append(
            Finding(
                code="unknown_location",
                severity=FindingSeverity.WARNING,
                message=f"Unknown location kind for TrackID {track.track_id}: {track.location or '(empty location)'}",
                track_id=track.track_id,
            )
        )

    for track in library.tracks:
        for cue in track.cues:
            if cue.cue_type is CueType.UNKNOWN:
                findings.append(
                    Finding(
                        code="unknown_cue_type",
                        severity=FindingSeverity.WARNING,
                        message=f"Unknown cue type on TrackID {track.track_id} at {cue.start:.3f}s",
                        track_id=track.track_id,
                    )
                )

    return tuple(findings)
