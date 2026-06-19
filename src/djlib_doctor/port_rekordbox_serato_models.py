from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .io_utils import render_json
from .port_cue_models import PortCueTiming
from .port_rekordbox_serato_policy import (
    CUE_POLICY,
    cue_counts_for_tracks,
    format_counts,
    merge_counts,
    namespace_policy,
    serato_format_capability,
)
from .serato_crate import safe_crate_filename

PORT_MANIFEST_SCHEMA_VERSION = "1.0"


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
        return {
            "intent": self.intent,
            **PortCueTiming(self.start_ms, self.end_ms, self.slot, self.label).to_dict(),
            "source_kind": self.source_kind,
            "source_type": self.source_type,
        }


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
    key: str = ""
    bpm: float | None = None
    comments: str = ""
    color: str = ""
    rating: int | None = None
    beatgrid_status: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "artist": self.artist,
            "path": self.path,
            "serato_portable_id": self.serato_portable_id,
            "source_cue_count": self.source_cue_count,
            "key": self.key,
            "bpm": self.bpm,
            "comments": self.comments,
            "color": self.color,
            "rating": self.rating,
            "beatgrid_status": self.beatgrid_status,
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
        return {
            "tracks": len(self.tracks),
            "cue_intents": cue_counts["serato_writable_slots"],
            "skipped": len(self.skipped),
            "unsupported_tracks": sum(1 for track in self.tracks if track.unsupported),
            "format_counts": format_counts(self.tracks),
            "cue_counts": cue_counts,
            "warnings": len(self.warnings),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": PORT_MANIFEST_SCHEMA_VERSION,
            "mode": "dry_run_only",
            "transfer_mode": self.transfer_mode,
            "scope": self.scope,
            "source_platform": "rekordbox_xml",
            "target_platform": "serato",
            "source_playlist": self.source_playlist,
            "target_crate_name": self.target_crate_name,
            "target_crate_filename": safe_crate_filename(self.target_crate_name),
            "summary": self.summary,
            "cue_policy": CUE_POLICY,
            "namespace_policy": namespace_policy(self.target_crate_name),
            "tracks": [track.to_dict() for track in self.tracks],
            "skipped": list(self.skipped),
            "warnings": list(self.warnings),
        }

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
        return {
            "crates": len(self.crates),
            "tracks": sum(len(crate.tracks) for crate in self.crates),
            "cue_intents": sum(crate.summary["cue_intents"] for crate in self.crates),
            "skipped": sum(len(crate.skipped) for crate in self.crates),
            "unsupported_tracks": sum(crate.summary["unsupported_tracks"] for crate in self.crates),
            "format_counts": merge_counts(crate.summary["format_counts"] for crate in self.crates),
            "cue_counts": merge_counts(crate.summary["cue_counts"] for crate in self.crates),
            "warnings": len(self.warnings),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": PORT_MANIFEST_SCHEMA_VERSION,
            "mode": "dry_run_only",
            "transfer_mode": self.transfer_mode,
            "scope": self.scope,
            "source_platform": "rekordbox_xml",
            "target_platform": "serato",
            "summary": self.summary,
            "cue_policy": CUE_POLICY,
            "namespace_policy": namespace_policy(),
            "crates": [crate.to_dict() for crate in self.crates],
            "warnings": list(self.warnings),
        }

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)
