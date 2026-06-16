from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import render_json
from .serato_crate import safe_crate_filename

PORT_MANIFEST_SCHEMA_VERSION = "1.0"
SERATO_MANAGED_CRATE_PREFIX = "RB - "
SERATO_FORMAT_CAPABILITIES = {
    ".aif": {"status": "supported_for_future_tag_writes", "cue_tags": "aiff_id3_geob_markers2", "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame."},
    ".aiff": {"status": "supported_for_future_tag_writes", "cue_tags": "aiff_id3_geob_markers2", "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame."},
    ".m4a": {"status": "supported_for_future_tag_writes", "cue_tags": "mp4_freeform_markersv2", "notes": "Serato markersv2 cue data is stored in an MP4 freeform atom."},
    ".mp4": {"status": "supported_for_future_tag_writes", "cue_tags": "mp4_freeform_markersv2", "notes": "Serato markersv2 cue data is stored in an MP4 freeform atom."},
    ".mp3": {"status": "supported_for_tag_writes", "cue_tags": "id3_geob_markers2", "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame."},
    ".flac": {"status": "future_uncertain", "cue_tags": "unknown", "notes": "Serato FLAC cue metadata needs more fixture-backed validation."},
    ".ogg": {"status": "future_uncertain", "cue_tags": "unknown", "notes": "Serato Ogg cue metadata needs more fixture-backed validation."},
    ".wav": {"status": "future_uncertain", "cue_tags": "unknown", "notes": "Serato WAV cue metadata needs more fixture-backed validation."},
}
CUE_POLICY = {
    "hotcues": "preserve matching Serato hotcue slots 1-8",
    "memory_cues": "promote to first unused Serato hotcue slot",
    "loops": "write saved-loop intent; hotcue loops also keep a hotcue intent",
    "writes_audio_tags": False,
}


@dataclass(frozen=True)
class SeratoCueIntent:
    intent: str
    start_ms: int
    end_ms: int | None = None
    slot: int | None = None
    label: str = ""
    source_kind: str = ""
    source_type: str = ""

    def to_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PortTrack:
    source_id: str
    title: str
    artist: str
    path: str
    serato_portable_id: str
    cue_intents: tuple[SeratoCueIntent, ...]
    unsupported: tuple[str, ...]
    source_cue_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "artist": self.artist,
            "path": self.path,
            "serato_portable_id": self.serato_portable_id,
            "source_cue_count": self.source_cue_count,
            "format_capability": serato_format_capability(self.path),
            "cue_intents": [intent.to_dict() for intent in self.cue_intents],
            "unsupported": list(self.unsupported),
        }


@dataclass(frozen=True)
class RekordboxToSeratoPlan:
    source_playlist: str
    target_crate_name: str
    tracks: tuple[PortTrack, ...]
    skipped: tuple[dict[str, str], ...]
    warnings: tuple[dict[str, str], ...] = ()
    scope: str = "playlist"
    transfer_mode: str = "full"

    @property
    def summary(self) -> dict[str, Any]:
        cue_counts = cue_counts_for_tracks(self.tracks)
        return {"tracks": len(self.tracks), "cue_intents": cue_counts["serato_writable_slots"], "skipped": len(self.skipped), "unsupported_tracks": sum(1 for track in self.tracks if track.unsupported), "format_counts": format_counts(self.tracks), "cue_counts": cue_counts, "warnings": len(self.warnings)}

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": PORT_MANIFEST_SCHEMA_VERSION, "mode": "dry_run_only", "transfer_mode": self.transfer_mode, "scope": self.scope, "source_platform": "rekordbox_xml", "target_platform": "serato", "source_playlist": self.source_playlist, "target_crate_name": self.target_crate_name, "target_crate_filename": safe_crate_filename(self.target_crate_name), "summary": self.summary, "cue_policy": CUE_POLICY, "namespace_policy": namespace_policy(self.target_crate_name), "tracks": [track.to_dict() for track in self.tracks], "skipped": list(self.skipped), "warnings": list(self.warnings)}

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)


@dataclass(frozen=True)
class RekordboxToSeratoBatchPlan:
    crates: tuple[RekordboxToSeratoPlan, ...]
    warnings: tuple[dict[str, str], ...] = ()
    scope: str = "playlists"
    transfer_mode: str = "full"

    @property
    def summary(self) -> dict[str, Any]:
        return {"crates": len(self.crates), "tracks": sum(len(crate.tracks) for crate in self.crates), "cue_intents": sum(crate.summary["cue_intents"] for crate in self.crates), "skipped": sum(len(crate.skipped) for crate in self.crates), "unsupported_tracks": sum(crate.summary["unsupported_tracks"] for crate in self.crates), "format_counts": merge_counts(crate.summary["format_counts"] for crate in self.crates), "cue_counts": merge_counts(crate.summary["cue_counts"] for crate in self.crates), "warnings": len(self.warnings)}

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": PORT_MANIFEST_SCHEMA_VERSION, "mode": "dry_run_only", "transfer_mode": self.transfer_mode, "scope": self.scope, "source_platform": "rekordbox_xml", "target_platform": "serato", "summary": self.summary, "cue_policy": CUE_POLICY, "namespace_policy": namespace_policy(), "crates": [crate.to_dict() for crate in self.crates], "warnings": list(self.warnings)}

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)


def serato_format_capability(path: str) -> dict[str, str]:
    extension = Path(path).suffix.lower()
    default = {"status": "unknown", "cue_tags": "unknown", "notes": "No Serato cue metadata policy is known for this extension."}
    return {"extension": extension.lstrip(".") or "unknown", **SERATO_FORMAT_CAPABILITIES.get(extension, default)}


def format_counts(tracks: tuple[PortTrack, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for track in tracks:
        extension = serato_format_capability(track.path)["extension"]
        counts[extension] = counts.get(extension, 0) + 1
    return counts


def cue_counts_for_tracks(tracks: tuple[PortTrack, ...]) -> dict[str, int]:
    return {"raw_rekordbox_cue_rows": sum(track.source_cue_count for track in tracks), "unique_track_cues": sum(track.source_cue_count for track in tracks), "serato_writable_slots": sum(len(track.cue_intents) for track in tracks)}


def merge_counts(counts_by_plan: Any) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counts in counts_by_plan:
        for key, value in counts.items():
            merged[key] = merged.get(key, 0) + int(value)
    return merged


def namespace_policy(target_crate_name: str | None = None) -> dict[str, object]:
    crate_name = target_crate_name or ""
    return {"managed_prefix": SERATO_MANAGED_CRATE_PREFIX, "target_uses_managed_prefix": crate_name.startswith(SERATO_MANAGED_CRATE_PREFIX) if crate_name else True, "preserve_existing_unmanaged_crates": True, "writes_live_serato_library": False, "writes_audio_tags": False}
