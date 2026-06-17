from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .serato_stage_models import SERATO_LIBRARY_ROOT_CONTAINER_ID, SERATO_LIBRARY_SPACE_ID
from .sqlite_utils import dynamic_insert, dynamic_update, require_columns


def write_crate_to_sqlite(
    conn: sqlite3.Connection, crate_name: str, tracks: tuple[dict[str, Any], ...], revision: int, now: int
) -> tuple[int, int]:
    container_id = _upsert_container(conn, crate_name, revision, now)
    conn.execute("DELETE FROM container_asset WHERE container_id = ?", (container_id,))
    created = reused = 0
    for index, track in enumerate(tracks, 1):
        asset_id, was_created = _upsert_asset(conn, track, revision, now)
        created += int(was_created)
        reused += int(not was_created)
        _insert_container_asset(conn, container_id, _upsert_space_asset(conn, asset_id), index, revision, now)
    return created, reused


def current_revision(conn: sqlite3.Connection) -> int:
    require_columns(conn, "serato", ("revision",), label="Serato")
    return int(conn.execute("SELECT revision FROM serato").fetchone()[0])


def update_revision(conn: sqlite3.Connection, revision: int) -> None:
    conn.execute("UPDATE serato SET revision = ?", (revision,))


def _upsert_container(conn: sqlite3.Connection, crate_name: str, revision: int, now: int) -> int:
    require_columns(conn, "container", ("id", "name", "parent_id", "type", "list_order"), label="Serato")
    existing = conn.execute(
        "SELECT id FROM container WHERE parent_id = ? AND name = ? COLLATE NOCASE AND type = 1",
        (SERATO_LIBRARY_ROOT_CONTAINER_ID, crate_name),
    ).fetchone()
    if existing:
        container_id = int(existing[0])
        dynamic_update(conn, "container", {"revision": revision}, "id = ?", (container_id,))
        return container_id
    next_order = conn.execute(
        "SELECT COALESCE(MAX(list_order), 0) + 1 FROM container WHERE parent_id = ?",
        (SERATO_LIBRARY_ROOT_CONTAINER_ID,),
    ).fetchone()[0]
    return dynamic_insert(
        conn,
        "container",
        {
            "revision": revision,
            "parent_id": SERATO_LIBRARY_ROOT_CONTAINER_ID,
            "name": crate_name,
            "type": 1,
            "list_order": next_order,
            "space_id": SERATO_LIBRARY_SPACE_ID,
            "time_added": now,
            "expanded": 0,
            "portable_id": "",
        },
    )


def _upsert_asset(conn: sqlite3.Connection, track: dict[str, Any], revision: int, now: int) -> tuple[int, bool]:
    require_columns(conn, "asset", ("id", "portable_id"), label="Serato")
    portable_id = str(track["serato_portable_id"])
    existing = conn.execute("SELECT id FROM asset WHERE portable_id = ? COLLATE NOCASE", (portable_id,)).fetchone()
    values = _asset_values(track, revision, now)
    if existing:
        asset_id = int(existing[0])
        dynamic_update(conn, "asset", values, "id = ?", (asset_id,))
        return asset_id, False
    return dynamic_insert(conn, "asset", values), True


def _asset_values(track: dict[str, Any], revision: int, now: int) -> dict[str, Any]:
    path = Path(str(track.get("path", "")))
    return {
        "revision": revision,
        "portable_id": str(track["serato_portable_id"]),
        "file_name": path.name,
        "file_size": path.stat().st_size if path.exists() else 0,
        "type": "audio",
        "format": path.suffix.lower().lstrip("."),
        "artist": track.get("artist", ""),
        "comments": "",
        "name": track.get("title", ""),
        "album": "",
        "genre": "",
        "key": "",
        "bpm": None,
        "length_ms": None,
        "time_added": now,
        "time_modified": now,
        "analysis_flags": 0,
        "architectures": 0,
    }


def _upsert_space_asset(conn: sqlite3.Connection, asset_id: int) -> int:
    require_columns(conn, "space_asset", ("id", "asset_id", "space_id"), label="Serato")
    existing = conn.execute(
        "SELECT id FROM space_asset WHERE asset_id = ? AND space_id = ?", (asset_id, SERATO_LIBRARY_SPACE_ID)
    ).fetchone()
    return (
        int(existing[0])
        if existing
        else dynamic_insert(
            conn, "space_asset", {"id": asset_id, "asset_id": asset_id, "space_id": SERATO_LIBRARY_SPACE_ID}
        )
    )


def _insert_container_asset(
    conn: sqlite3.Connection, container_id: int, space_asset_id: int, list_order: int, revision: int, now: int
) -> None:
    require_columns(conn, "container_asset", ("container_id", "space_asset_id"), label="Serato")
    dynamic_insert(
        conn,
        "container_asset",
        {
            "revision": revision,
            "container_id": container_id,
            "space_asset_id": space_asset_id,
            "list_order": list_order,
            "time_added": now,
        },
    )
