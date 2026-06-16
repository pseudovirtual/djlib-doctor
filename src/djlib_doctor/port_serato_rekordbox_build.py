from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from .port_serato_rekordbox_models import RekordboxPortTrack, SeratoToRekordboxPlan
from .serato_crate import read_serato_crate
from .sqlite_utils import quote_identifier


def build_serato_to_rekordbox_plan(serato_library_dir: Path, crate_path: Path, collection_root: Path, playlist_name: str | None = None) -> SeratoToRekordboxPlan:
    crate = read_serato_crate(crate_path)
    assets = _read_assets_by_portable_id(serato_library_dir / "root.sqlite")
    tracks, skipped = _build_tracks(crate.tracks, assets, collection_root)
    return SeratoToRekordboxPlan(str(crate_path), playlist_name or crate_path.stem, tracks, skipped)


def build_serato_track_to_rekordbox_plan(serato_library_dir: Path, portable_id: str, collection_root: Path, playlist_name: str | None = None, transfer_mode: str = "full") -> SeratoToRekordboxPlan:
    _validate_transfer_mode(transfer_mode)
    assets = _read_assets_by_portable_id(serato_library_dir / "root.sqlite")
    tracks, skipped = _build_tracks((portable_id,), assets, collection_root)
    return SeratoToRekordboxPlan("TRACK", playlist_name or f"Track {Path(portable_id).stem}", tracks, skipped, "track", transfer_mode)


def build_serato_collection_to_rekordbox_plan(serato_library_dir: Path, collection_root: Path, playlist_name: str | None = None, transfer_mode: str = "full") -> SeratoToRekordboxPlan:
    _validate_transfer_mode(transfer_mode)
    assets = _read_assets_by_portable_id(serato_library_dir / "root.sqlite")
    tracks, skipped = _build_tracks(tuple(assets), assets, collection_root)
    return SeratoToRekordboxPlan("COLLECTION", playlist_name or "Serato Collection", tracks, skipped, "collection", transfer_mode)


def _build_tracks(portable_ids: tuple[str, ...], assets: dict[str, dict[str, Any]], collection_root: Path) -> tuple[tuple[RekordboxPortTrack, ...], tuple[dict[str, str], ...]]:
    tracks = []
    skipped = []
    for index, portable_id in enumerate(portable_ids, 1):
        if not _is_local_portable_id(portable_id):
            skipped.append({"portable_id": portable_id, "reason": "not_local_file"})
            continue
        asset = assets.get(portable_id.lower(), {})
        tracks.append(_track(index, portable_id, asset, collection_root))
    return tuple(tracks), tuple(skipped)


def _track(index: int, portable_id: str, asset: dict[str, Any], collection_root: Path) -> RekordboxPortTrack:
    return RekordboxPortTrack(
        track_id=str(index),
        portable_id=portable_id,
        path=str(collection_root / portable_id),
        title=str(asset.get("name") or Path(portable_id).stem),
        artist=str(asset.get("artist") or ""),
        album=str(asset.get("album") or ""),
        genre=str(asset.get("genre") or ""),
        key=str(asset.get("key") or ""),
        bpm=_optional_float(asset.get("bpm")),
        length_ms=_optional_int(asset.get("length_ms")),
    )


def _read_assets_by_portable_id(root_sqlite: Path) -> dict[str, dict[str, Any]]:
    conn = sqlite3.connect(f"file:{root_sqlite}?mode=ro", uri=True)
    try:
        columns = _table_columns(conn, "asset")
        wanted = [column for column in ("portable_id", "name", "artist", "album", "genre", "key", "bpm", "length_ms") if column in columns]
        if "portable_id" not in wanted:
            raise ValueError("Serato asset table does not include portable_id")
        rows = conn.execute(f"SELECT {', '.join(quote_identifier(column) for column in wanted)} FROM asset").fetchall()
        assets = {}
        for row in rows:
            item = dict(zip(wanted, row))
            portable_id = str(item.get("portable_id") or "")
            if portable_id:
                assets[portable_id.lower()] = item
        return assets
    finally:
        conn.close()


def _table_columns(conn: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row[1] for row in conn.execute(f"PRAGMA table_info({quote_identifier(table)})"))


def _is_local_portable_id(value: str) -> bool:
    lowered = value.lower()
    return bool(value) and ":" not in lowered and not lowered.startswith(("soundcloud", "spotify", "tidal", "beatport"))


def _validate_transfer_mode(value: str) -> None:
    if value not in {"full", "cues-only", "match-only"}:
        raise ValueError(f"Unsupported transfer mode: {value}")


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)
