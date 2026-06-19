from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .io_utils import render_json, write_json
from .port_cue_models import PortCueTiming
from .rekordbox_uri import path_to_file_url
from .serato_crate import read_serato_crate
from .serato_file_tags import read_serato_markers2_file_tags
from .sqlite_utils import quote_identifier, table_columns
from .transfer_modes import validate_transfer_mode

REKORDBOX_PORT_SCHEMA_VERSION = "1.0"
TagReader = Callable[[Path], tuple[dict[str, Any], ...]]


@dataclass(frozen=True)
class RekordboxPortCue:
    kind: str
    cue_type: str
    start_ms: int
    end_ms: int | None = None
    slot: int | None = None
    label: str = ""
    color: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "cue_type": self.cue_type,
            **PortCueTiming(self.start_ms, self.end_ms, self.slot, self.label).to_dict(),
            "color": self.color,
        }


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
    cue_status: dict[str, str] | None = None

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


def build_serato_to_rekordbox_plan(
    serato_library_dir: Path,
    crate_path: Path,
    collection_root: Path,
    playlist_name: str | None = None,
    tag_reader: TagReader | None = None,
) -> SeratoToRekordboxPlan:
    crate = read_serato_crate(crate_path)
    assets = _read_assets_by_portable_id(serato_library_dir / "root.sqlite")
    tracks, skipped = _build_tracks(crate.tracks, assets, collection_root, tag_reader)
    return SeratoToRekordboxPlan(str(crate_path), playlist_name or crate_path.stem, tracks, skipped)


def build_serato_track_to_rekordbox_plan(
    serato_library_dir: Path,
    portable_id: str,
    collection_root: Path,
    playlist_name: str | None = None,
    transfer_mode: str = "full",
    tag_reader: TagReader | None = None,
) -> SeratoToRekordboxPlan:
    validate_transfer_mode(transfer_mode)
    assets = _read_assets_by_portable_id(serato_library_dir / "root.sqlite")
    tracks, skipped = _build_tracks((portable_id,), assets, collection_root, tag_reader)
    return SeratoToRekordboxPlan(
        "TRACK", playlist_name or f"Track {Path(portable_id).stem}", tracks, skipped, "track", transfer_mode
    )


def build_serato_collection_to_rekordbox_plan(
    serato_library_dir: Path,
    collection_root: Path,
    playlist_name: str | None = None,
    transfer_mode: str = "full",
    tag_reader: TagReader | None = None,
) -> SeratoToRekordboxPlan:
    validate_transfer_mode(transfer_mode)
    assets = _read_assets_by_portable_id(serato_library_dir / "root.sqlite")
    tracks, skipped = _build_tracks(tuple(assets), assets, collection_root, tag_reader)
    return SeratoToRekordboxPlan(
        "COLLECTION", playlist_name or "Serato Collection", tracks, skipped, "collection", transfer_mode
    )


def write_serato_to_rekordbox_plan(plan: SeratoToRekordboxPlan, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "port-manifest.json"
    xml_path = out_dir / "rekordbox-preview.xml"
    write_json(manifest_path, plan.to_dict())
    xml_path.write_text(render_rekordbox_xml_preview(plan) + "\n", encoding="utf-8")
    return {"manifest": str(manifest_path), "rekordbox_xml_preview": str(xml_path)}


def render_rekordbox_xml_preview(plan: SeratoToRekordboxPlan) -> str:
    root = ET.Element("DJ_PLAYLISTS", {"Version": "1.0.0"})
    ET.SubElement(root, "PRODUCT", {"Name": "djlib-doctor", "Version": "0.1.0", "Company": "djlib-doctor"})
    collection = ET.SubElement(root, "COLLECTION", {"Entries": str(len(plan.tracks))})
    for track in plan.tracks:
        track_element = ET.SubElement(collection, "TRACK", _track_attrs(track))
        for cue in track.cues:
            ET.SubElement(track_element, "POSITION_MARK", _cue_attrs(cue))
    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", {"Type": "0", "Name": "ROOT", "Count": "1"})
    playlist = ET.SubElement(
        root_node, "NODE", {"Name": plan.target_playlist, "Type": "1", "KeyType": "0", "Entries": str(len(plan.tracks))}
    )
    for track in plan.tracks:
        ET.SubElement(playlist, "TRACK", {"Key": track.track_id})
    _indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def _build_tracks(
    portable_ids: tuple[str, ...],
    assets: dict[str, dict[str, Any]],
    collection_root: Path,
    tag_reader: TagReader | None,
) -> tuple[tuple[RekordboxPortTrack, ...], tuple[dict[str, str], ...]]:
    tracks = []
    skipped = []
    for index, portable_id in enumerate(portable_ids, 1):
        if not _is_local_portable_id(portable_id):
            skipped.append({"portable_id": portable_id, "reason": "not_local_file"})
            continue
        tracks.append(_track(index, portable_id, assets.get(portable_id.lower(), {}), collection_root, tag_reader))
    return tuple(tracks), tuple(skipped)


def _track(
    index: int, portable_id: str, asset: dict[str, Any], collection_root: Path, tag_reader: TagReader | None
) -> RekordboxPortTrack:
    path = collection_root / portable_id
    cues, cue_status = _cue_data(path, tag_reader)
    return RekordboxPortTrack(
        str(index),
        portable_id,
        str(path),
        str(asset.get("name") or Path(portable_id).stem),
        str(asset.get("artist") or ""),
        str(asset.get("album") or ""),
        str(asset.get("genre") or ""),
        str(asset.get("key") or ""),
        _optional_float(asset.get("bpm")),
        _optional_int(asset.get("length_ms")),
        cues,
        cue_status,
    )


def _cue_data(path: Path, tag_reader: TagReader | None) -> tuple[tuple[RekordboxPortCue, ...], dict[str, str]]:
    if path.suffix.lower() == ".wav":
        return (), {"status": "unsupported_format", "reason": "wav_has_no_serato_tag_container"}
    cues = _cues(path, tag_reader)
    status = "read_from_audio_file_tags" if cues else "no_markers2_tag"
    return cues, {"status": status}


def _cues(path: Path, tag_reader: TagReader | None) -> tuple[RekordboxPortCue, ...]:
    reader = tag_reader or read_serato_markers2_file_tags
    return tuple(RekordboxPortCue(**cue) for cue in reader(path))


def _read_assets_by_portable_id(root_sqlite: Path) -> dict[str, dict[str, Any]]:
    conn = sqlite3.connect(f"file:{root_sqlite}?mode=ro", uri=True)
    try:
        columns = table_columns(conn, "asset")
        wanted = [
            column
            for column in ("portable_id", "name", "artist", "album", "genre", "key", "bpm", "length_ms")
            if column in columns
        ]
        if "portable_id" not in wanted:
            raise ValueError("Serato asset table does not include portable_id")
        rows = conn.execute(f"SELECT {', '.join(quote_identifier(column) for column in wanted)} FROM asset").fetchall()
        return _assets_by_portable_id(wanted, rows)
    finally:
        conn.close()


def _assets_by_portable_id(columns: list[str], rows: list[tuple[Any, ...]]) -> dict[str, dict[str, Any]]:
    assets = {}
    for row in rows:
        item = dict(zip(columns, row))
        portable_id = str(item.get("portable_id") or "")
        if portable_id:
            assets[portable_id.lower()] = item
    return assets


def _is_local_portable_id(value: str) -> bool:
    lowered = value.lower()
    return bool(value) and ":" not in lowered and not lowered.startswith(("soundcloud", "spotify", "tidal", "beatport"))


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _track_attrs(track: RekordboxPortTrack) -> dict[str, str]:
    attrs = {"TrackID": track.track_id, "Name": track.title, "Artist": track.artist, "Location": _file_url(track.path)}
    attrs.update(
        {
            key: value
            for key, value in {"Album": track.album, "Genre": track.genre, "Tonality": track.key}.items()
            if value
        }
    )
    if track.bpm is not None:
        attrs["AverageBpm"] = f"{track.bpm:g}"
    if track.length_ms is not None:
        attrs["TotalTime"] = str(int(round(track.length_ms / 1000)))
    return attrs


def _cue_attrs(cue: RekordboxPortCue) -> dict[str, str]:
    attrs = {
        "Type": "4" if cue.cue_type == "loop" else "0",
        "Start": f"{cue.start_ms / 1000:.3f}",
        "Num": "" if cue.slot is None else str(cue.slot),
    }
    if cue.label:
        attrs["Name"] = cue.label
    if cue.end_ms is not None:
        attrs["End"] = f"{cue.end_ms / 1000:.3f}"
    return attrs


def _file_url(path: str) -> str:
    return path_to_file_url(path)


def _indent(element: ET.Element, level: int = 0) -> None:
    indentation = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = indentation + "  "
        for child in element:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indentation
    if level and (not element.tail or not element.tail.strip()):
        element.tail = indentation


__all__ = [
    "REKORDBOX_PORT_SCHEMA_VERSION",
    "RekordboxPortTrack",
    "SeratoToRekordboxPlan",
    "build_serato_collection_to_rekordbox_plan",
    "build_serato_to_rekordbox_plan",
    "build_serato_track_to_rekordbox_plan",
    "render_rekordbox_xml_preview",
    "write_serato_to_rekordbox_plan",
]
