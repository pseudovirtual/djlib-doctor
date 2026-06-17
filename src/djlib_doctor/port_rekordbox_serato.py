from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cues import CueType
from .io_utils import read_json, render_json, write_json
from .library_model import LibraryCue, LibraryTrack, rekordbox_xml_to_library
from .locations import LocationKind
from .rekordbox_xml import parse_rekordbox_xml
from .serato_crate import read_serato_crate, safe_crate_filename, write_serato_crate
from .transfer_modes import validate_transfer_mode

PORT_MANIFEST_SCHEMA_VERSION = "1.0"
SERATO_MANAGED_CRATE_PREFIX = "RB - "
SERATO_FORMAT_CAPABILITIES = {
    ".aif": {
        "status": "supported_for_future_tag_writes",
        "cue_tags": "aiff_id3_geob_markers2",
        "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame.",
    },
    ".aiff": {
        "status": "supported_for_future_tag_writes",
        "cue_tags": "aiff_id3_geob_markers2",
        "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame.",
    },
    ".m4a": {
        "status": "supported_for_future_tag_writes",
        "cue_tags": "mp4_freeform_markersv2",
        "notes": "Serato markersv2 cue data is stored in an MP4 freeform atom.",
    },
    ".mp4": {
        "status": "supported_for_future_tag_writes",
        "cue_tags": "mp4_freeform_markersv2",
        "notes": "Serato markersv2 cue data is stored in an MP4 freeform atom.",
    },
    ".mp3": {
        "status": "supported_for_tag_writes",
        "cue_tags": "id3_geob_markers2",
        "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame.",
    },
    ".flac": {
        "status": "future_uncertain",
        "cue_tags": "unknown",
        "notes": "Serato FLAC cue metadata needs more fixture-backed validation.",
    },
    ".ogg": {
        "status": "future_uncertain",
        "cue_tags": "unknown",
        "notes": "Serato Ogg cue metadata needs more fixture-backed validation.",
    },
    ".wav": {
        "status": "future_uncertain",
        "cue_tags": "unknown",
        "notes": "Serato WAV cue metadata needs more fixture-backed validation.",
    },
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


def build_rekordbox_to_serato_plan(
    rekordbox_xml: Path,
    playlist_name: str,
    crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX,
    transfer_mode: str = "full",
) -> RekordboxToSeratoPlan:
    return _build_playlist_plan(
        rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml)), playlist_name, crate_prefix, transfer_mode
    )


def build_rekordbox_to_serato_plans(
    rekordbox_xml: Path,
    playlist_names: list[str] | tuple[str, ...],
    crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX,
    transfer_mode: str = "full",
) -> RekordboxToSeratoBatchPlan:
    source = rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml))
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
    source = rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml))
    return _build_scoped_plan(
        source, (track_id,), f"TRACK / {track_id}", f"{crate_prefix}Track {track_id}", "track", transfer_mode
    )


def build_rekordbox_collection_to_serato_plan(
    rekordbox_xml: Path, crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX, transfer_mode: str = "full"
) -> RekordboxToSeratoPlan:
    source = rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml))
    track_ids = tuple(track.source_id for track in source.tracks)
    return _build_scoped_plan(source, track_ids, "COLLECTION", f"{crate_prefix}Collection", "collection", transfer_mode)


def write_rekordbox_to_serato_plan(
    plan: RekordboxToSeratoPlan | RekordboxToSeratoBatchPlan, out_dir: Path
) -> dict[str, str | list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "port-manifest.json"
    unsupported_path = out_dir / "unsupported.csv"
    write_json(manifest_path, plan.to_dict())
    if isinstance(plan, RekordboxToSeratoBatchPlan):
        crate_paths = []
        for crate_plan in plan.crates:
            crate_path = _unique_crate_path(out_dir, crate_plan.target_crate_name, crate_paths)
            write_serato_crate(crate_path, tuple(track.serato_portable_id for track in crate_plan.tracks))
            crate_paths.append(crate_path)
        _write_unsupported_csv(unsupported_path, plan)
        return {
            "manifest": str(manifest_path),
            "crate_previews": [str(path) for path in crate_paths],
            "unsupported_csv": str(unsupported_path),
        }
    crate_path = out_dir / f"{safe_crate_filename(plan.target_crate_name)}.crate"
    write_serato_crate(crate_path, tuple(track.serato_portable_id for track in plan.tracks))
    _write_unsupported_csv(unsupported_path, plan)
    return {"manifest": str(manifest_path), "crate_preview": str(crate_path), "unsupported_csv": str(unsupported_path)}


def read_playlist_names(path: Path) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def render_rekordbox_to_serato_summary(plan: RekordboxToSeratoPlan | RekordboxToSeratoBatchPlan) -> str:
    summary = plan.summary
    lines = [
        "Dry-run Serato summary",
        f"Crates: {summary.get('crates', 1)}",
        f"Tracks: {summary['tracks']}",
        f"Skipped: {summary['skipped']}",
        f"Cue intents: {summary['cue_intents']}",
        f"Warnings: {summary['warnings']}",
    ]
    for label, key in (("Formats", "format_counts"), ("Cue counts", "cue_counts")):
        counts = summary.get(key, {})
        if counts:
            lines.append(label + ": " + ", ".join(f"{name}={count}" for name, count in sorted(counts.items())))
    return "\n".join(lines)


def verify_rekordbox_to_serato_plan(manifest_path: Path, crate_preview_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    expected_tracks = [track["serato_portable_id"] for track in manifest.get("tracks", [])]
    crate = read_serato_crate(crate_preview_path)
    checks = {
        "mode": "passed" if manifest.get("mode") == "dry_run_only" else "failed",
        "target_platform": "passed" if manifest.get("target_platform") == "serato" else "failed",
        "crate_track_order": "passed" if list(crate.tracks) == expected_tracks else "failed",
    }
    return {"passed": all(value == "passed" for value in checks.values()), "checks": checks}


def serato_format_capability(path: str) -> dict[str, str]:
    extension = Path(path).suffix.lower()
    default = {
        "status": "unknown",
        "cue_tags": "unknown",
        "notes": "No Serato cue metadata policy is known for this extension.",
    }
    return {"extension": extension.lstrip(".") or "unknown", **SERATO_FORMAT_CAPABILITIES.get(extension, default)}


def format_counts(tracks: tuple[PortTrack, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for track in tracks:
        extension = serato_format_capability(track.path)["extension"]
        counts[extension] = counts.get(extension, 0) + 1
    return counts


def cue_counts_for_tracks(tracks: tuple[PortTrack, ...]) -> dict[str, int]:
    return {
        "raw_rekordbox_cue_rows": sum(track.source_cue_count for track in tracks),
        "unique_track_cues": sum(track.source_cue_count for track in tracks),
        "serato_writable_slots": sum(len(track.cue_intents) for track in tracks),
    }


def merge_counts(counts_by_plan: Any) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counts in counts_by_plan:
        for key, value in counts.items():
            merged[key] = merged.get(key, 0) + int(value)
    return merged


def namespace_policy(target_crate_name: str | None = None) -> dict[str, object]:
    crate_name = target_crate_name or ""
    return {
        "managed_prefix": SERATO_MANAGED_CRATE_PREFIX,
        "target_uses_managed_prefix": crate_name.startswith(SERATO_MANAGED_CRATE_PREFIX) if crate_name else True,
        "preserve_existing_unmanaged_crates": True,
        "writes_live_serato_library": False,
        "writes_audio_tags": False,
    }


def _build_playlist_plan(
    source: Any, playlist_name: str, crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX, transfer_mode: str = "full"
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
        source, playlist.track_ids, playlist.name, f"{crate_prefix}{playlist.name}", "playlist", transfer_mode
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
    source: Any, track_ids: tuple[str, ...], source_name: str, target_name: str, scope: str, transfer_mode: str
) -> RekordboxToSeratoPlan:
    validate_transfer_mode(transfer_mode)
    tracks_by_id = source.track_by_id()
    tracks = []
    skipped = []
    for track_id in track_ids:
        track = tracks_by_id.get(track_id)
        if track is None:
            skipped.append({"track_id": track_id, "reason": "playlist_reference_missing_collection_track"})
        elif track.location_kind != LocationKind.LOCAL_FILE.value or track.path is None:
            skipped.append(
                {"track_id": track_id, "title": track.title, "artist": track.artist, "reason": "not_local_file"}
            )
        else:
            tracks.append(_port_track(track, include_cues=transfer_mode != "match-only"))
    return RekordboxToSeratoPlan(
        source_name, target_name, tuple(tracks), tuple(skipped), scope=scope, transfer_mode=transfer_mode
    )


def _port_track(track: LibraryTrack, include_cues: bool = True) -> PortTrack:
    cue_intents, unsupported = _cue_intents(track.cues) if include_cues else ((), ())
    beatgrid_status = "unsupported_not_written_to_serato_yet" if track.beatgrid else ""
    return PortTrack(
        track.source_id,
        track.title,
        track.artist,
        str(track.path or ""),
        track.serato_portable_id,
        cue_intents,
        unsupported,
        len(track.cues),
        track.key,
        track.bpm,
        track.comments,
        track.color,
        track.rating,
        beatgrid_status,
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
        intents.append(
            SeratoCueIntent(
                "serato_saved_loop",
                cue.start_ms,
                cue.end_ms,
                slot,
                cue.label or f"Loop {slot + 1}",
                cue.kind,
                cue.cue_type,
            )
        )


def _hotcue_intent(cue: LibraryCue, slot: int, label: str = "") -> SeratoCueIntent:
    return SeratoCueIntent(
        "serato_hotcue", cue.start_ms, None, slot, label or cue.label or chr(ord("A") + slot), cue.kind, cue.cue_type
    )


def _next_unused_slot(used: set[int]) -> int | None:
    return next((index for index in range(8) if index not in used), None)


def _write_unsupported_csv(path: Path, plan: RekordboxToSeratoPlan | RekordboxToSeratoBatchPlan) -> None:
    rows = []
    plans = plan.crates if isinstance(plan, RekordboxToSeratoBatchPlan) else (plan,)
    for crate_plan in plans:
        rows.extend(
            {"track_id": track.source_id, "artist": track.artist, "title": track.title, "issue": issue}
            for track in crate_plan.tracks
            for issue in track.unsupported
        )
        rows.extend(
            {
                "track_id": row.get("track_id", ""),
                "artist": row.get("artist", ""),
                "title": row.get("title", ""),
                "issue": row.get("reason", ""),
            }
            for row in crate_plan.skipped
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["track_id", "artist", "title", "issue"])
        writer.writeheader()
        writer.writerows(rows)


def _unique_crate_path(out_dir: Path, crate_name: str, existing_paths: list[Path]) -> Path:
    base = safe_crate_filename(crate_name)
    candidate = out_dir / f"{base}.crate"
    index = 2
    while candidate in set(existing_paths):
        candidate = out_dir / f"{base} ({index}).crate"
        index += 1
    return candidate


__all__ = [
    "PORT_MANIFEST_SCHEMA_VERSION",
    "SERATO_FORMAT_CAPABILITIES",
    "SERATO_MANAGED_CRATE_PREFIX",
    "PortTrack",
    "RekordboxToSeratoBatchPlan",
    "RekordboxToSeratoPlan",
    "SeratoCueIntent",
    "build_rekordbox_collection_to_serato_plan",
    "build_rekordbox_to_serato_plan",
    "build_rekordbox_to_serato_plans",
    "build_rekordbox_track_to_serato_plan",
    "read_playlist_names",
    "render_rekordbox_to_serato_summary",
    "serato_format_capability",
    "verify_rekordbox_to_serato_plan",
    "write_rekordbox_to_serato_plan",
]
