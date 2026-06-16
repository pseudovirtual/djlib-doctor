from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET

from .io_utils import write_json
from .port_serato_rekordbox_models import SeratoToRekordboxPlan


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
        ET.SubElement(collection, "TRACK", _track_attrs(track))
    playlists = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists, "NODE", {"Type": "0", "Name": "ROOT", "Count": "1"})
    playlist = ET.SubElement(root_node, "NODE", {"Name": plan.target_playlist, "Type": "1", "KeyType": "0", "Entries": str(len(plan.tracks))})
    for track in plan.tracks:
        ET.SubElement(playlist, "TRACK", {"Key": track.track_id})
    _indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def _track_attrs(track) -> dict[str, str]:
    attrs = {"TrackID": track.track_id, "Name": track.title, "Artist": track.artist, "Location": _file_url(track.path)}
    optional = {"Album": track.album, "Genre": track.genre, "Tonality": track.key}
    attrs.update({key: value for key, value in optional.items() if value})
    if track.bpm is not None:
        attrs["AverageBpm"] = f"{track.bpm:g}"
    if track.length_ms is not None:
        attrs["TotalTime"] = str(int(round(track.length_ms / 1000)))
    return attrs


def _file_url(path: str) -> str:
    return "file://localhost" + quote(path)


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
