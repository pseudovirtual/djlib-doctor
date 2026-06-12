from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any
from urllib.parse import quote
import xml.etree.ElementTree as ET
from .io_utils import render_json, write_json
from .serato_crate import read_serato_crate
REKORDBOX_PORT_SCHEMA_VERSION = "1.0"
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
    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "portable_id": self.portable_id,
            "path": self.path,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "genre": self.genre,
            "key": self.key,
            "bpm": self.bpm,
            "length_ms": self.length_ms,
        }
@dataclass(frozen=True)
class SeratoToRekordboxPlan:
    source_crate: str
    target_playlist: str
    tracks: tuple[RekordboxPortTrack, ...]
    skipped: tuple[dict[str, str], ...]
    @property
    def summary(self) -> dict[str, int]:
        return {"tracks": len(self.tracks), "skipped": len(self.skipped)}
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REKORDBOX_PORT_SCHEMA_VERSION,
            "mode": "dry_run_only",
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
) -> SeratoToRekordboxPlan:
    root_sqlite = serato_library_dir / "root.sqlite"
    crate = read_serato_crate(crate_path)
    assets = _read_assets_by_portable_id(root_sqlite)
    tracks = []
    skipped = []
    for index, portable_id in enumerate(crate.tracks, 1):
        if not _is_local_portable_id(portable_id):
            skipped.append({"portable_id": portable_id, "reason": "not_local_file"})
            continue
        asset = assets.get(portable_id.lower(), {})
        local_path = collection_root / portable_id
        tracks.append(
            RekordboxPortTrack(
                track_id=str(index),
                portable_id=portable_id,
                path=str(local_path),
                title=str(asset.get("name") or Path(portable_id).stem),
                artist=str(asset.get("artist") or ""),
                album=str(asset.get("album") or ""),
                genre=str(asset.get("genre") or ""),
                key=str(asset.get("key") or ""),
                bpm=_optional_float(asset.get("bpm")),
                length_ms=_optional_int(asset.get("length_ms")),
            )
        )
    return SeratoToRekordboxPlan(
        source_crate=str(crate_path),
        target_playlist=playlist_name or crate_path.stem,
        tracks=tuple(tracks),
        skipped=tuple(skipped),
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
        attrs = {
            "TrackID": track.track_id,
            "Name": track.title,
            "Artist": track.artist,
            "Location": _file_url(track.path),
        }
        if track.album:
            attrs["Album"] = track.album
        if track.genre:
            attrs["Genre"] = track.genre
        if track.key:
            attrs["Tonality"] = track.key
        if track.bpm is not None:
            attrs["AverageBpm"] = f"{track.bpm:g}"
        if track.length_ms is not None:
            attrs["TotalTime"] = str(int(round(track.length_ms / 1000)))
        ET.SubElement(collection, "TRACK", attrs)
    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", {"Type": "0", "Name": "ROOT", "Count": "1"})
    playlist = ET.SubElement(root_node, "NODE", {"Name": plan.target_playlist, "Type": "1", "KeyType": "0", "Entries": str(len(plan.tracks))})
    for track in plan.tracks:
        ET.SubElement(playlist, "TRACK", {"Key": track.track_id})
    _indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
def _read_assets_by_portable_id(root_sqlite: Path) -> dict[str, dict[str, Any]]:
    conn = sqlite3.connect(f"file:{root_sqlite}?mode=ro", uri=True)
    try:
        columns = _table_columns(conn, "asset")
        wanted = [column for column in ("portable_id", "name", "artist", "album", "genre", "key", "bpm", "length_ms") if column in columns]
        if "portable_id" not in wanted:
            raise ValueError("Serato asset table does not include portable_id")
        rows = conn.execute(f"SELECT {', '.join(_quote_identifier(column) for column in wanted)} FROM asset").fetchall()
        assets = {}
        for row in rows:
            item = dict(zip(wanted, row))
            portable_id = str(item.get("portable_id") or "")
            if portable_id:
                assets[portable_id.lower()] = item
        return assets
    finally:
        conn.close()
def _is_local_portable_id(value: str) -> bool:
    lowered = value.lower()
    return bool(value) and ":" not in lowered and not lowered.startswith(("soundcloud", "spotify", "tidal", "beatport"))
def _file_url(path: str) -> str:
    return "file://localhost" + quote(path)
def _table_columns(conn: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row[1] for row in conn.execute(f"PRAGMA table_info({_quote_identifier(table)})"))
def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
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
