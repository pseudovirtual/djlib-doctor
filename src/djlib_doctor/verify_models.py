from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .io_utils import render_json
from .rekordbox_xml import Track


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
        data = {"code": self.code, "severity": self.severity.value, "message": self.message}
        for key in ("track_id", "playlist", "path"):
            value = getattr(self, key)
            if value:
                data[key] = value
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
        action_map = {
            "missing_local_file": "Run `djlib-doctor snapshot` and then `djlib-doctor plan missing-files` to review replacement candidates.",
            "duplicate_track_id": "Run `djlib-doctor snapshot` and then `djlib-doctor plan duplicates` to choose cue-safe survivor records.",
            "missing_playlist_track": "Inspect playlist references before removing or rebuilding playlists.",
            "unknown_location": "Review unknown locations; djlib-doctor will not guess whether they are safe local files or placeholders.",
            "unknown_cue_type": "Review unknown cue types before migrating or comparing cue data.",
        }
        actions.extend(text for code, text in action_map.items() if code in finding_codes)
        if not actions and self.passed:
            actions.append("Create a snapshot before planning any cleanup or comparing this export to another export.")
        return tuple(actions)

    def render_text(self) -> str:
        lines = _summary_lines(self)
        _append_findings(lines, "Failures", self.failures)
        _append_findings(lines, "Warnings", self.warnings)
        _append_text_list(lines, "Suggested next actions", self.next_actions)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": "pass" if self.passed else "fail",
            "source": {"type": "rekordbox_xml", "path": self.source_path, "check_files": self.check_files},
            "counts": {"collection_tracks": self.collection_tracks, "playlist_references": self.playlist_refs, "local_file_tracks": self.local_file_tracks, "streaming_placeholders": self.streaming_placeholders, "unknown_location_tracks": self.unknown_location_tracks, "missing_local_files": len(self.missing_local_files), "cues": self.cue_count, "hotcues": self.hotcue_count, "memory_cues": self.memory_cue_count, "loops": self.loop_count, "failures": len(self.failures), "warnings": len(self.warnings)},
            "failures": [finding.to_dict() for finding in self.failures],
            "warnings": [finding.to_dict() for finding in self.warnings],
            "next_actions": list(self.next_actions),
        }

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)


def _summary_lines(report: VerificationReport) -> list[str]:
    return [f"djlib-doctor verification: {'PASS' if report.passed else 'FAIL'}", f"Source: {report.source_path or '(in-memory library)'}", f"File existence check: {'on' if report.check_files else 'off'}", f"Collection tracks: {report.collection_tracks}", f"Playlist references: {report.playlist_refs}", f"Local file-backed tracks: {report.local_file_tracks}", f"Streaming placeholders: {report.streaming_placeholders}", f"Unknown location tracks: {report.unknown_location_tracks}", f"Missing local files: {len(report.missing_local_files)}", f"Cues: {report.cue_count} ({report.hotcue_count} hotcue, {report.memory_cue_count} memory, {report.loop_count} loop)", f"Failures: {len(report.failures)}", f"Warnings: {len(report.warnings)}"]


def _append_findings(lines: list[str], title: str, findings: tuple[Finding, ...]) -> None:
    _append_text_list(lines, title, tuple(finding.message for finding in findings))


def _append_text_list(lines: list[str], title: str, values: tuple[str, ...]) -> None:
    if values:
        lines.extend(("", f"{title}:"))
        lines.extend(f"- {value}" for value in values)
