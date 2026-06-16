from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .io_utils import render_json

REKORDBOX_PORT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class RekordboxPortCue:
    kind: str
    cue_type: str
    start_ms: int
    end_ms: int | None = None
    slot: int | None = None
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RekordboxPortTrack:
    track_id: str
    portable_id: str
    path: str
    title: str
    artist: str = ""
    album: str = ""
    genre: str = ""
    key: str = ""
    bpm: float | None = None
    length_ms: int | None = None
    cues: tuple[RekordboxPortCue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = self.__dict__.copy()
        data["cues"] = [cue.to_dict() for cue in self.cues]
        return data


@dataclass(frozen=True)
class SeratoToRekordboxPlan:
    source_crate: str
    target_playlist: str
    tracks: tuple[RekordboxPortTrack, ...]
    skipped: tuple[dict[str, str], ...]
    scope: str = "crate"
    transfer_mode: str = "full"

    @property
    def summary(self) -> dict[str, int]:
        return {"tracks": len(self.tracks), "skipped": len(self.skipped)}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REKORDBOX_PORT_SCHEMA_VERSION,
            "mode": "dry_run_only",
            "transfer_mode": self.transfer_mode,
            "scope": self.scope,
            "source_platform": "serato",
            "target_platform": "rekordbox_xml",
            "source_crate": self.source_crate,
            "target_playlist": self.target_playlist,
            "summary": self.summary,
            "tracks": [track.to_dict() for track in self.tracks],
            "skipped": list(self.skipped),
        }

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)
