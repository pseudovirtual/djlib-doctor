from __future__ import annotations

from pathlib import Path
from typing import Any

from .cues import CueType
from .library_model import LibraryCue, LibraryTrack, rekordbox_xml_to_library
from .locations import LocationKind
from .port_serato_models import SERATO_MANAGED_CRATE_PREFIX, PortTrack, RekordboxToSeratoBatchPlan, RekordboxToSeratoPlan, SeratoCueIntent
from .rekordbox_xml import parse_rekordbox_xml
from .serato_crate import safe_crate_filename


def build_rekordbox_to_serato_plan(rekordbox_xml: Path, playlist_name: str, crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX) -> RekordboxToSeratoPlan:
    return _build_plan_from_library(rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml)), playlist_name, crate_prefix)


def build_rekordbox_to_serato_plans(rekordbox_xml: Path, playlist_names: list[str] | tuple[str, ...], crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX) -> RekordboxToSeratoBatchPlan:
    source = rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml))
    plans = []
    warnings = []
    crate_filenames: dict[str, str] = {}
    for playlist_name in playlist_names:
        plan = _build_plan_from_library(source, playlist_name, crate_prefix)
        plans.append(plan)
        warnings.extend(plan.warnings)
        filename = safe_crate_filename(plan.target_crate_name)
        if filename in crate_filenames:
            warnings.append({"code": "target_crate_filename_collision", "target_crate_filename": filename, "first_playlist": crate_filenames[filename], "playlist": plan.source_playlist})
        else:
            crate_filenames[filename] = plan.source_playlist
    return RekordboxToSeratoBatchPlan(tuple(plans), tuple(warnings))


def _build_plan_from_library(source: Any, playlist_name: str, crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX) -> RekordboxToSeratoPlan:
    playlists = {playlist.name: playlist for playlist in source.playlists}
    playlist = playlists.get(playlist_name)
    warnings = []
    if playlist is None:
        trimmed_matches = [playlist for name, playlist in playlists.items() if name.strip() == playlist_name.strip()]
        if len(trimmed_matches) == 1:
            playlist = trimmed_matches[0]
            warnings.append({"code": "playlist_name_matched_after_trimming", "requested_playlist": playlist_name, "matched_playlist": playlist.name})
    if playlist is None:
        raise ValueError(f"Playlist not found: {playlist_name}. Known playlists: {', '.join(sorted(playlists))}")
    tracks_by_id = source.track_by_id()
    tracks = []
    skipped = []
    for track_id in playlist.track_ids:
        track = tracks_by_id.get(track_id)
        if track is None:
            skipped.append({"track_id": track_id, "reason": "playlist_reference_missing_collection_track"})
        elif track.location_kind != LocationKind.LOCAL_FILE.value or track.path is None:
            skipped.append({"track_id": track_id, "title": track.title, "artist": track.artist, "reason": "not_local_file"})
        else:
            tracks.append(_port_track(track))
    return RekordboxToSeratoPlan(playlist.name, f"{crate_prefix}{playlist.name}", tuple(tracks), tuple(skipped), tuple(warnings))


def _port_track(track: LibraryTrack) -> PortTrack:
    cue_intents, unsupported = _cue_intents(track.cues)
    return PortTrack(track.source_id, track.title, track.artist, str(track.path or ""), track.serato_portable_id, cue_intents, unsupported, len(track.cues))


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
            _append_memory_cue(cue, intents, unsupported, used_hotcue_slots)
        if cue.cue_type == CueType.LOOP.value:
            _append_loop(cue, intents, unsupported, used_loop_slots)
    return tuple(intents), tuple(unsupported)


def _append_memory_cue(cue: LibraryCue, intents: list[SeratoCueIntent], unsupported: list[str], used: set[int]) -> None:
    slot = _next_unused_slot(used)
    if slot is None:
        unsupported.append("no_serato_hotcue_slot_for_memory_cue")
    else:
        used.add(slot)
        intents.append(_hotcue_intent(cue, slot, label=cue.label or f"Memory {slot + 1}"))


def _append_loop(cue: LibraryCue, intents: list[SeratoCueIntent], unsupported: list[str], used: set[int]) -> None:
    slot = cue.slot if cue.slot is not None and 0 <= cue.slot <= 7 else _next_unused_slot(used)
    if slot is None:
        unsupported.append("no_serato_loop_slot")
    else:
        used.add(slot)
        intents.append(SeratoCueIntent("serato_saved_loop", cue.start_ms, cue.end_ms, slot, cue.label or f"Loop {slot + 1}", cue.kind, cue.cue_type))


def _hotcue_intent(cue: LibraryCue, slot: int, label: str = "") -> SeratoCueIntent:
    return SeratoCueIntent("serato_hotcue", cue.start_ms, None, slot, label or cue.label or chr(ord("A") + slot), cue.kind, cue.cue_type)


def _next_unused_slot(used: set[int]) -> int | None:
    return next((index for index in range(8) if index not in used), None)
