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
from .serato_crate import read_serato_crate, safe_crate_filename, write_serato_crate


PORT_MANIFEST_SCHEMA_VERSION = "1.0"

SERATO_MANAGED_CRATE_PREFIX = "RB - "


SERATO_FORMAT_CAPABILITIES: dict[str, dict[str, str]] = {
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
        "status": "likely_supported_future_work",
        "cue_tags": "id3_geob_markers2",
        "notes": "MP3 should use an ID3 GEOB-style Serato marker frame; not implemented.",
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

    @property
    def summary(self) -> dict[str, Any]:
        cue_counts = _cue_counts(self.tracks)
        return {
            "tracks": len(self.tracks),
            "cue_intents": cue_counts["serato_writable_slots"],
            "skipped": len(self.skipped),
            "unsupported_tracks": sum(1 for track in self.tracks if track.unsupported),
            "format_counts": _format_counts(self.tracks),
            "cue_counts": cue_counts,
            "warnings": len(self.warnings),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": PORT_MANIFEST_SCHEMA_VERSION,
            "mode": "dry_run_only",
            "source_platform": "rekordbox_xml",
            "target_platform": "serato",
            "source_playlist": self.source_playlist,
            "target_crate_name": self.target_crate_name,
            "target_crate_filename": safe_crate_filename(self.target_crate_name),
            "summary": self.summary,
            "cue_policy": {
                "hotcues": "preserve matching Serato hotcue slots 1-8",
                "memory_cues": "promote to first unused Serato hotcue slot",
                "loops": "write saved-loop intent; hotcue loops also keep a hotcue intent",
                "writes_audio_tags": False,
            },
            "namespace_policy": _namespace_policy(self.target_crate_name),
            "tracks": [track.to_dict() for track in self.tracks],
            "skipped": list(self.skipped),
            "warnings": list(self.warnings),
        }

    def render_json(self, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(self.to_dict(), indent=2, sort_keys=True)
        return json.dumps(self.to_dict(), sort_keys=True)


@dataclass(frozen=True)
class RekordboxToSeratoBatchPlan:
    crates: tuple[RekordboxToSeratoPlan, ...]
    warnings: tuple[dict[str, str], ...] = ()

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "crates": len(self.crates),
            "tracks": sum(len(crate.tracks) for crate in self.crates),
            "cue_intents": sum(crate.summary["cue_intents"] for crate in self.crates),
            "skipped": sum(len(crate.skipped) for crate in self.crates),
            "unsupported_tracks": sum(crate.summary["unsupported_tracks"] for crate in self.crates),
            "format_counts": _merge_counts(crate.summary["format_counts"] for crate in self.crates),
            "cue_counts": _merge_counts(crate.summary["cue_counts"] for crate in self.crates),
            "warnings": len(self.warnings),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": PORT_MANIFEST_SCHEMA_VERSION,
            "mode": "dry_run_only",
            "source_platform": "rekordbox_xml",
            "target_platform": "serato",
            "summary": self.summary,
            "cue_policy": {
                "hotcues": "preserve matching Serato hotcue slots 1-8",
                "memory_cues": "promote to first unused Serato hotcue slot",
                "loops": "write saved-loop intent; hotcue loops also keep a hotcue intent",
                "writes_audio_tags": False,
            },
            "namespace_policy": _namespace_policy(),
            "crates": [crate.to_dict() for crate in self.crates],
            "warnings": list(self.warnings),
        }

    def render_json(self, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(self.to_dict(), indent=2, sort_keys=True)
        return json.dumps(self.to_dict(), sort_keys=True)


def build_rekordbox_to_serato_plan(
    rekordbox_xml: Path,
    playlist_name: str,
    crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX,
) -> RekordboxToSeratoPlan:
    source = rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml))
    return _build_plan_from_library(source, playlist_name, crate_prefix=crate_prefix)


def build_rekordbox_to_serato_plans(
    rekordbox_xml: Path,
    playlist_names: list[str] | tuple[str, ...],
    crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX,
) -> RekordboxToSeratoBatchPlan:
    source = rekordbox_xml_to_library(parse_rekordbox_xml(rekordbox_xml))
    plans = []
    warnings = []
    crate_filenames: dict[str, str] = {}
    for playlist_name in playlist_names:
        plan = _build_plan_from_library(source, playlist_name, crate_prefix=crate_prefix)
        plans.append(plan)
        warnings.extend(plan.warnings)
        crate_filename = safe_crate_filename(plan.target_crate_name)
        existing = crate_filenames.get(crate_filename)
        if existing is not None:
            warnings.append(
                {
                    "code": "target_crate_filename_collision",
                    "target_crate_filename": crate_filename,
                    "first_playlist": existing,
                    "playlist": plan.source_playlist,
                }
            )
        else:
            crate_filenames[crate_filename] = plan.source_playlist
    return RekordboxToSeratoBatchPlan(crates=tuple(plans), warnings=tuple(warnings))


def write_rekordbox_to_serato_plan(
    plan: RekordboxToSeratoPlan | RekordboxToSeratoBatchPlan,
    out_dir: Path,
) -> dict[str, str | list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "port-manifest.json"
    unsupported_path = out_dir / "unsupported.csv"
    manifest_path.write_text(plan.render_json(pretty=True) + "\n", encoding="utf-8")

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
    return {
        "manifest": str(manifest_path),
        "crate_preview": str(crate_path),
        "unsupported_csv": str(unsupported_path),
    }


def read_playlist_names(path: Path) -> tuple[str, ...]:
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            names.append(stripped)
    return tuple(names)


def serato_format_capability(path: str) -> dict[str, str]:
    extension = Path(path).suffix.lower()
    capability = SERATO_FORMAT_CAPABILITIES.get(
        extension,
        {
            "status": "unknown",
            "cue_tags": "unknown",
            "notes": "No Serato cue metadata policy is known for this extension.",
        },
    )
    return {"extension": extension.lstrip(".") or "unknown", **capability}


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
    format_counts = summary.get("format_counts", {})
    if format_counts:
        lines.append("Formats: " + ", ".join(f"{name}={count}" for name, count in sorted(format_counts.items())))
    cue_counts = summary.get("cue_counts", {})
    if cue_counts:
        lines.append(
            "Cue counts: "
            + ", ".join(f"{name}={count}" for name, count in sorted(cue_counts.items()))
        )
    return "\n".join(lines)


def verify_rekordbox_to_serato_plan(manifest_path: Path, crate_preview_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_tracks = [track["serato_portable_id"] for track in manifest.get("tracks", [])]
    crate = read_serato_crate(crate_preview_path)
    checks = {
        "mode": "passed" if manifest.get("mode") == "dry_run_only" else "failed",
        "target_platform": "passed" if manifest.get("target_platform") == "serato" else "failed",
        "crate_track_order": "passed" if list(crate.tracks) == expected_tracks else "failed",
    }
    return {"passed": all(value == "passed" for value in checks.values()), "checks": checks}


def _build_plan_from_library(
    source: Any,
    playlist_name: str,
    crate_prefix: str = SERATO_MANAGED_CRATE_PREFIX,
) -> RekordboxToSeratoPlan:
    playlists = {playlist.name: playlist for playlist in source.playlists}
    playlist = playlists.get(playlist_name)
    warnings = []
    if playlist is None:
        trimmed = playlist_name.strip()
        trimmed_matches = [playlist for name, playlist in playlists.items() if name.strip() == trimmed]
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
        warnings=tuple(warnings),
    )


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
        source_cue_count=len(track.cues),
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


def _write_unsupported_csv(path: Path, plan: RekordboxToSeratoPlan | RekordboxToSeratoBatchPlan) -> None:
    rows = []
    plans = plan.crates if isinstance(plan, RekordboxToSeratoBatchPlan) else (plan,)
    for crate_plan in plans:
        for track in crate_plan.tracks:
            for issue in track.unsupported:
                rows.append({"track_id": track.source_id, "artist": track.artist, "title": track.title, "issue": issue})
        for row in crate_plan.skipped:
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


def _format_counts(tracks: tuple[PortTrack, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for track in tracks:
        extension = serato_format_capability(track.path)["extension"]
        counts[extension] = counts.get(extension, 0) + 1
    return counts


def _cue_counts(tracks: tuple[PortTrack, ...]) -> dict[str, int]:
    unique_cues: set[tuple[str, str, str, int | None, int, int | None]] = set()
    for track in tracks:
        for intent in track.cue_intents:
            unique_cues.add(
                (
                    track.source_id,
                    intent.source_kind,
                    intent.source_type,
                    intent.slot,
                    intent.start_ms,
                    intent.end_ms,
                )
            )
    return {
        "raw_rekordbox_cue_rows": sum(track.source_cue_count for track in tracks),
        "unique_track_cues": sum(track.source_cue_count for track in tracks),
        "serato_writable_slots": sum(len(track.cue_intents) for track in tracks),
    }


def _merge_counts(counts_by_plan: Any) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counts in counts_by_plan:
        for key, value in counts.items():
            merged[key] = merged.get(key, 0) + int(value)
    return merged


def _namespace_policy(target_crate_name: str | None = None) -> dict[str, object]:
    crate_name = target_crate_name or ""
    return {
        "managed_prefix": SERATO_MANAGED_CRATE_PREFIX,
        "target_uses_managed_prefix": crate_name.startswith(SERATO_MANAGED_CRATE_PREFIX) if crate_name else True,
        "preserve_existing_unmanaged_crates": True,
        "writes_live_serato_library": False,
        "writes_audio_tags": False,
    }


def _unique_crate_path(out_dir: Path, crate_name: str, existing_paths: list[Path]) -> Path:
    base = safe_crate_filename(crate_name)
    candidate = out_dir / f"{base}.crate"
    index = 2
    existing = set(existing_paths)
    while candidate in existing:
        candidate = out_dir / f"{base} ({index}).crate"
        index += 1
    return candidate
