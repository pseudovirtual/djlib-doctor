from __future__ import annotations

from pathlib import Path
from typing import Any

from .rekordbox_db_read import read_rekordbox_master_db
from .rekordbox_xml import RekordboxLibrary


def build_pyrekordbox_import_operations(
    live_db: Path, tracks: tuple[dict[str, Any], ...], content_table: str, cue_table: str
) -> list[dict[str, Any]]:
    library = read_rekordbox_master_db(live_db)
    operations = []
    existing = _existing_library_paths(library)
    next_id = _next_library_track_id(library)
    next_cue_id = _next_library_cue_id(library)
    for track in tracks:
        values = _content_values(track)
        key = (values["FolderPath"], values["FileNameL"])
        if key in existing:
            content_id = existing[key]
            operations.append(
                {
                    "operation": "update",
                    "table": content_table,
                    "values": _update_values(values),
                    "where": {"ID": content_id},
                }
            )
        else:
            content_id = next_id
            values["ID"] = next_id
            operations.append({"operation": "insert", "table": content_table, "values": values})
            next_id += 1
        cue_ops, next_cue_id = _cue_operations(track, cue_table, content_id, next_cue_id)
        operations.extend(cue_ops)
    return operations


def _existing_library_paths(library: RekordboxLibrary) -> dict[tuple[str, str], int]:
    return {
        _split_db_path(str(track.path)): int(track.track_id)
        for track in library.tracks
        if track.path is not None and str(track.track_id).isdigit()
    }


def _next_library_track_id(library: RekordboxLibrary) -> int:
    ids = [int(track.track_id) for track in library.tracks if str(track.track_id).isdigit()]
    return max(ids, default=0) + 1


def _next_library_cue_id(library: RekordboxLibrary) -> int:
    return sum(len(track.cues) for track in library.tracks) + 1


def _content_values(track: dict[str, Any]) -> dict[str, Any]:
    folder, filename = _split_db_path(str(track.get("path") or ""))
    values = {"FolderPath": folder, "FileNameL": filename, "Title": track.get("title") or Path(filename).stem}
    optional = {"BPM": track.get("bpm"), "Length": track.get("length_ms")}
    values.update({column: value for column, value in optional.items() if value not in (None, "")})
    return values


def _update_values(values: dict[str, Any]) -> dict[str, Any]:
    return {column: value for column, value in values.items() if column != "ID"}


def _split_db_path(path: str) -> tuple[str, str]:
    item = Path(path)
    folder = "" if str(item.parent) == "." else str(item.parent)
    return folder, item.name


def _cue_operations(
    track: dict[str, Any], cue_table: str, content_id: int, next_id: int
) -> tuple[list[dict[str, Any]], int]:
    cues = tuple(track.get("cues") or ())
    if not cues:
        return [], next_id
    operations = [{"operation": "delete", "table": cue_table, "where": {"ContentID": content_id}}]
    for cue in cues:
        operations.append({"operation": "insert", "table": cue_table, "values": _cue_values(cue, content_id, next_id)})
        next_id += 1
    return operations, next_id


def _cue_values(cue: dict[str, Any], content_id: int, cue_id: int) -> dict[str, Any]:
    return {
        "ID": cue_id,
        "ContentID": content_id,
        "InMsec": int(cue["start_ms"]),
        "OutMsec": 0 if cue.get("end_ms") is None else int(cue["end_ms"]),
        "Kind": 4 if cue.get("cue_type") == "loop" else 0,
        "Comment": str(cue.get("label") or ""),
    }
