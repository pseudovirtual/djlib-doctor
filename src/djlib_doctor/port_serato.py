from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
from typing import Any

from .cues import CueType
from .library_model import LibraryCue, LibraryTrack, rekordbox_xml_to_library
from .locations import LocationKind
from .rekordbox_xml import parse_rekordbox_xml
from .serato_crate import safe_crate_filename, write_serato_crate


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
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "slot": self.slot,
            "label": self.label,
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

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "artist": self.artist,
            "path": self.path,
            "serato_portable_id": self.serato_portable_id,
            "cue_intents": [intent.to_dict() for intent in self.cue_intents],
            "unsupported": list(self.unsupported),
        }


@dataclass(frozen=True)
class RekordboxToSeratoPlan:
    source_playlist: str
    target_crate_name: str
    tracks: tuple[PortTrack, ...]
    skipped: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": PORT_MANIFEST_SCHEMA_VERSION,
            "mode": "dry_run_only",
            "source_platform": "rekordbox_xml",
            "target_platform": "serato",
            "source_playlist": self.source_playlist,
            "target_crate_name": self.target_crate_name,
            "summary": {
                "tracks": len(self.tracks),
                "cue_intents": sum(len(track.cue_intents) for track in self.tracks),
                "skipped": len(self.skipped),
                "unsupported_tracks": sum(1 for track in self.tracks if track.unsupported),
            },
            "cue_policy": {
                "hotcues": "preserve matching Serato hotcue slots 1-8",
                "memory_cues": "promote to first unused Serato hotcue slot",
                "loops": "write saved-loop intent; hotcue loops also keep a hotcue intent",
                "writes_audio_tags": False,
            },
            "tracks": [track.to_dict() for track in self.tracks],
            "skipped": list(self.skipped),
        }

    def render_json(self, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(self.to_dict(), indent=2, sort_keys=True)
        return json.dumps(self.to_dict(), sort_keys=True)


def build_rekordbox_to_serato_plan(
    rekordbox_xml: Path,
    playlist_name: str,
    crate_prefix: str = "RB - ",
) -> RekordboxToSeratoPlan:
    source = rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml))
    playlists = {playlist.name: playlist for playlist in source.playlists}
    playlist = playlists.get(playlist_name)
    if playlist is None:
        known = ", ".join(sorted(playlists))
        raise ValueError(f"Playlist not found: {playlist_name}. Known playlists: {known}")

    tracks_by_id = source.track_by_id()
    tracks = []
    skipped = []
    for track_id in playlist.track_ids:
        track = tracks_by_id.get(track_id)
        if track is None:
            skipped.append({"track_id": track_id, "reason": "playlist_reference_missing_collection_track"})
            continue
        if track.location_kind != LocationKind.LOCAL_FILE.value or track.path is None:
            skipped.append({"track_id": track_id, "title": track.title, "artist": track.artist, "reason": "not_local_file"})
            continue
        tracks.append(_port_track(track))

    return RekordboxToSeratoPlan(
        source_playlist=playlist.name,
        target_crate_name=f"{crate_prefix}{playlist.name}",
        tracks=tuple(tracks),
        skipped=tuple(skipped),
    )


def write_rekordbox_to_serato_plan(plan: RekordboxToSeratoPlan, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "port-manifest.json"
    crate_path = out_dir / f"{safe_crate_filename(plan.target_crate_name)}.crate"
    unsupported_path = out_dir / "unsupported.csv"
    manifest_path.write_text(plan.render_json(pretty=True) + "\n", encoding="utf-8")
    write_serato_crate(crate_path, tuple(track.serato_portable_id for track in plan.tracks))
    _write_unsupported_csv(unsupported_path, plan)
    return {
        "manifest": str(manifest_path),
        "crate_preview": str(crate_path),
        "unsupported_csv": str(unsupported_path),
    }


def _port_track(track: LibraryTrack) -> PortTrack:
    cue_intents, unsupported = _cue_intents(track.cues)
    return PortTrack(
        source_id=track.source_id,
        title=track.title,
        artist=track.artist,
        path=str(track.path or ""),
        serato_portable_id=track.serato_portable_id,
        cue_intents=cue_intents,
        unsupported=unsupported,
    )


def _cue_intents(cues: tuple[LibraryCue, ...]) -> tuple[tuple[SeratoCueIntent, ...], tuple[str, ...]]:
    intents = []
    unsupported = []
    used_hotcue_slots: set[int] = set()
    used_loop_slots: set[int] = set()

    for cue in sorted(cues, key=lambda item: (item.slot if item.slot is not None else 99, item.start_seconds)):
        if cue.kind == "hotcue" and cue.slot is not None:
            if 0 <= cue.slot <= 7:
                used_hotcue_slots.add(cue.slot)
                intents.append(_hotcue_intent(cue, cue.slot))
            else:
                unsupported.append(f"hotcue_slot_out_of_serato_range:{cue.slot}")
        elif cue.cue_type != CueType.LOOP.value:
            slot = _next_unused_slot(used_hotcue_slots)
            if slot is None:
                unsupported.append("no_serato_hotcue_slot_for_memory_cue")
            else:
                used_hotcue_slots.add(slot)
                intents.append(_hotcue_intent(cue, slot, label=cue.label or f"Memory {slot + 1}"))

        if cue.cue_type == CueType.LOOP.value:
            slot = cue.slot if cue.slot is not None and 0 <= cue.slot <= 7 else _next_unused_slot(used_loop_slots)
            if slot is None:
                unsupported.append("no_serato_loop_slot")
            else:
                used_loop_slots.add(slot)
                intents.append(
                    SeratoCueIntent(
                        intent="serato_saved_loop",
                        start_ms=cue.start_ms,
                        end_ms=cue.end_ms,
                        slot=slot,
                        label=cue.label or f"Loop {slot + 1}",
                        source_kind=cue.kind,
                        source_type=cue.cue_type,
                    )
                )

    return tuple(intents), tuple(unsupported)


def _hotcue_intent(cue: LibraryCue, slot: int, label: str = "") -> SeratoCueIntent:
    return SeratoCueIntent(
        intent="serato_hotcue",
        start_ms=cue.start_ms,
        slot=slot,
        label=label or cue.label or chr(ord("A") + slot),
        source_kind=cue.kind,
        source_type=cue.cue_type,
    )


def _next_unused_slot(used: set[int]) -> int | None:
    for index in range(8):
        if index not in used:
            return index
    return None


def _write_unsupported_csv(path: Path, plan: RekordboxToSeratoPlan) -> None:
    rows = []
    for track in plan.tracks:
        for issue in track.unsupported:
            rows.append({"track_id": track.source_id, "artist": track.artist, "title": track.title, "issue": issue})
    for row in plan.skipped:
        rows.append(
            {
                "track_id": row.get("track_id", ""),
                "artist": row.get("artist", ""),
                "title": row.get("title", ""),
                "issue": row.get("reason", ""),
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["track_id", "artist", "title", "issue"])
        writer.writeheader()
        writer.writerows(rows)
