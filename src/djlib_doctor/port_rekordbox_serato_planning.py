from __future__ import annotations

from pathlib import Path

from .locations import LocationKind
from .port_rekordbox_serato_cues import cue_intents
from .port_rekordbox_serato_models import PortTrack, RekordboxToSeratoBatchPlan, RekordboxToSeratoPlan
from .port_rekordbox_serato_policy import SERATO_MANAGED_CRATE_PREFIX
from .rekordbox_xml import RekordboxLibrary, Track, parse_rekordbox_xml
from .serato_crate import safe_crate_filename
from .transfer_modes import validate_transfer_mode


def build_rekordbox_to_serato_plan(
    rekordbox_xml: Path,
    playlist_name: str,
    crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX,
    transfer_mode: str = "full",
) -> RekordboxToSeratoPlan:
    return _build_playlist_plan(parse_rekordbox_xml(rekordbox_xml), playlist_name, crate_prefix, transfer_mode)


def build_rekordbox_to_serato_plans(
    rekordbox_xml: Path,
    playlist_names: list[str] | tuple[str, ...],
    crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX,
    transfer_mode: str = "full",
) -> RekordboxToSeratoBatchPlan:
    source = parse_rekordbox_xml(rekordbox_xml)
    plans = []
    warnings = []
    crate_filenames: dict[str, str] = {}
    for playlist_name in playlist_names:
        plan = _build_playlist_plan(source, playlist_name, crate_prefix, transfer_mode)
        plans.append(plan)
        warnings.extend(plan.warnings)
        filename = safe_crate_filename(plan.target_crate_name)
        if filename in crate_filenames:
            warnings.append(
                {
                    "code": "target_crate_filename_collision",
                    "target_crate_filename": filename,
                    "first_playlist": crate_filenames[filename],
                    "playlist": plan.source_playlist,
                }
            )
        else:
            crate_filenames[filename] = plan.source_playlist
    return RekordboxToSeratoBatchPlan(tuple(plans), tuple(warnings), transfer_mode=transfer_mode)


def build_rekordbox_track_to_serato_plan(
    rekordbox_xml: Path, track_id: str, crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX, transfer_mode: str = "full"
) -> RekordboxToSeratoPlan:
    source = parse_rekordbox_xml(rekordbox_xml)
    return _build_scoped_plan(
        source, (track_id,), f"TRACK / {track_id}", f"{crate_prefix}Track {track_id}", "track", transfer_mode
    )


def build_rekordbox_collection_to_serato_plan(
    rekordbox_xml: Path, crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX, transfer_mode: str = "full"
) -> RekordboxToSeratoPlan:
    source = parse_rekordbox_xml(rekordbox_xml)
    track_ids = tuple(track.track_id for track in source.tracks)
    return _build_scoped_plan(source, track_ids, "COLLECTION", f"{crate_prefix}Collection", "collection", transfer_mode)


def _build_playlist_plan(
    source: RekordboxLibrary,
    playlist_name: str,
    crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX,
    transfer_mode: str = "full",
) -> RekordboxToSeratoPlan:
    playlists = {playlist.name: playlist for playlist in source.playlists}
    playlist = playlists.get(playlist_name)
    warnings = []
    if playlist is None:
        trimmed_matches = [playlist for name, playlist in playlists.items() if name.strip() == playlist_name.strip()]
        if len(trimmed_matches) == 1:
            playlist = trimmed_matches[0]
            warnings.append(
                {
                    "code": "playlist_name_matched_after_trimming",
                    "requested_playlist": playlist_name,
                    "matched_playlist": playlist.name,
                }
            )
    if playlist is None:
        raise ValueError(f"Playlist not found: {playlist_name}. Known playlists: {', '.join(sorted(playlists))}")
    plan = _build_scoped_plan(
        source, playlist.entries, playlist.name, f"{crate_prefix}{playlist.name}", "playlist", transfer_mode
    )
    return RekordboxToSeratoPlan(
        plan.source_playlist,
        plan.target_crate_name,
        plan.tracks,
        plan.skipped,
        tuple(warnings),
        plan.scope,
        plan.transfer_mode,
    )


def _build_scoped_plan(
    source: RekordboxLibrary,
    track_ids: tuple[str, ...],
    source_name: str,
    target_name: str,
    scope: str,
    transfer_mode: str,
) -> RekordboxToSeratoPlan:
    validate_transfer_mode(transfer_mode)
    tracks_by_id = {track.track_id: track for track in source.tracks}
    tracks = []
    skipped = []
    for track_id in track_ids:
        track = tracks_by_id.get(track_id)
        if track is None:
            skipped.append({"track_id": track_id, "reason": "playlist_reference_missing_collection_track"})
        elif track.location_kind is not LocationKind.LOCAL_FILE or track.path is None:
            skipped.append(
                {
                    "track_id": track_id,
                    "title": track.name or "",
                    "artist": track.artist or "",
                    "reason": "not_local_file",
                }
            )
        else:
            tracks.append(_port_track(track, include_cues=transfer_mode != "match-only"))
    return RekordboxToSeratoPlan(
        source_name, target_name, tuple(tracks), tuple(skipped), scope=scope, transfer_mode=transfer_mode
    )


def _port_track(track: Track, include_cues: bool = True) -> PortTrack:
    intents, unsupported = cue_intents(track.cues) if include_cues else ((), ())
    beatgrid_status = "unsupported_not_written_to_serato_yet" if track.beatgrid else ""
    return PortTrack(
        track.track_id,
        track.name or "",
        track.artist or "",
        str(track.path or ""),
        "" if track.path is None else str(track.path).replace("\\", "/").lstrip("/"),
        intents,
        unsupported,
        len(track.cues),
        track.key,
        track.bpm,
        track.comments,
        track.color,
        track.rating,
        beatgrid_status,
    )
