from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .cues import Cue, CueKind, CueType
from .locations import parse_location
from .rekordbox_pyrekordbox import open_master_database
from .rekordbox_uri import path_to_file_url
from .rekordbox_xml import Playlist, PlaylistRef, RekordboxLibrary, Track

DbOpener = Callable[..., Any]

FILE_TYPES = {1: "MP3", 4: "M4A", 5: "FLAC", 11: "WAV", 12: "AIFF"}


def read_rekordbox_master_db(path: Path, key: str = "", opener: DbOpener = open_master_database) -> RekordboxLibrary:
    db = opener(path, key=key, unlock=True)
    try:
        return library_from_pyrekordbox_db(db)
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            close()


def library_from_pyrekordbox_db(db: Any) -> RekordboxLibrary:
    contents = tuple(_all(db.get_content()))
    cues_by_track = _cues_by_track(_all(db.get_cue()) if hasattr(db, "get_cue") else ())
    playlists, refs = _playlists(db)
    return RekordboxLibrary(
        tracks=tuple(_track(row, cues_by_track.get(str(_value(row, "ID")), ())) for row in contents),
        playlist_refs=refs,
        playlists=playlists,
    )


def _track(row: Any, cues: tuple[Cue, ...]) -> Track:
    path = _track_path(row)
    location = path_to_file_url(path) if path else None
    kind, local_path = parse_location(location)
    return Track(
        track_id=str(_value(row, "ID", default="")),
        name=_optional_str(_value(row, "Title")),
        artist=_related_name(row, "ArtistName", "Artist", "Name"),
        location=location,
        location_kind=kind,
        path=local_path,
        format=_file_type(_value(row, "FileType")),
        cues=cues,
        bpm=_bpm(_value(row, "BPM")),
        key=_related_name(row, "KeyName", "Key", "ScaleName") or "",
        color=_related_name(row, "ColorName", "Color", "Commnt") or "",
        rating=_optional_int(_value(row, "Rating")),
        comments=_optional_str(_value(row, "Commnt")) or "",
    )


def _cues_by_track(rows: tuple[Any, ...]) -> dict[str, tuple[Cue, ...]]:
    cues: dict[str, list[Cue]] = {}
    for row in rows:
        content_id = str(_value(row, "ContentID", default=""))
        cues.setdefault(content_id, []).append(_cue(row))
    return {track_id: tuple(items) for track_id, items in cues.items()}


def _cue(row: Any) -> Cue:
    hotcue = _hotcue_slot(row)
    kind = CueKind.HOTCUE if hotcue is not None else CueKind.MEMORY
    raw_end = _value(row, "OutMsec")
    cue_type = _cue_type(raw_end)
    return Cue(
        kind=kind,
        cue_type=cue_type,
        start=_msec(_value(row, "InMsec")),
        end=_msec(raw_end) if cue_type is CueType.LOOP else None,
        slot=hotcue if kind is CueKind.HOTCUE else None,
        name=_optional_str(_value(row, "Name", "Comment")),
        color=_optional_str(_value(row, "Color")),
    )


def _hotcue_slot(row: Any) -> int | None:
    raw_kind = _optional_int(_value(row, "Kind"))
    if not _bool_value(_value(row, "is_hot_cue")) and (raw_kind is None or raw_kind < 1):
        return None
    return raw_kind - 1 if raw_kind is not None and raw_kind >= 1 else None


def _cue_type(raw_end: Any) -> CueType:
    end = _optional_float(raw_end)
    return CueType.LOOP if end is not None and end > 0 else CueType.CUE


def _playlists(db: Any) -> tuple[tuple[Playlist, ...], tuple[PlaylistRef, ...]]:
    if not hasattr(db, "get_playlist") or not hasattr(db, "get_playlist_songs"):
        return (), ()
    rows = tuple(_all(db.get_playlist()))
    songs = sorted(_all(db.get_playlist_songs()), key=lambda row: _optional_int(_value(row, "TrackNo")) or 0)
    names = {str(_value(row, "ID", default="")): _playlist_path(row, rows) for row in rows}
    entries_by_playlist: dict[str, list[str]] = {}
    for song in songs:
        playlist_id = str(_value(song, "PlaylistID", default=""))
        entries_by_playlist.setdefault(playlist_id, []).append(str(_value(song, "ContentID", default="")))
    playlists = []
    refs = []
    for row in rows:
        playlist_id = str(_value(row, "ID", default=""))
        if _is_playlist(row) and playlist_id in entries_by_playlist:
            name = names[playlist_id]
            entries = tuple(entries_by_playlist[playlist_id])
            playlists.append(Playlist(name=name, entries=entries))
            refs.extend(PlaylistRef(key=track_id, playlist=name) for track_id in entries)
    return tuple(playlists), tuple(refs)


def _playlist_path(row: Any, rows: tuple[Any, ...]) -> str:
    by_id = {str(_value(item, "ID", default="")): item for item in rows}
    names = [_optional_str(_value(row, "Name")) or ""]
    parent_id = _optional_str(_value(row, "ParentID"))
    while parent_id and parent_id in by_id:
        parent = by_id[parent_id]
        name = _optional_str(_value(parent, "Name"))
        if name:
            names.append(name)
        parent_id = _optional_str(_value(parent, "ParentID"))
    return " / ".join(reversed([name for name in names if name]))


def _track_path(row: Any) -> Path | None:
    folder = _optional_str(_value(row, "FolderPath", "rb_LocalFolderPath"))
    filename = _optional_str(_value(row, "FileNameL", "FileNameS"))
    if not folder:
        return None
    path = Path(folder)
    return path if not filename or path.name == filename else path / filename


def _value(row: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(row, dict) and name in row:
            return row[name]
        if hasattr(row, name):
            return getattr(row, name)
    return default


def _related_name(row: Any, value_name: str, relation_name: str, relation_value: str) -> str | None:
    direct = _optional_str(_value(row, value_name))
    if direct:
        return direct
    relation = _value(row, relation_name)
    return _optional_str(_value(relation, relation_value)) if relation is not None else None


def _all(query: Any) -> tuple[Any, ...]:
    return tuple(query.all()) if hasattr(query, "all") else tuple(query or ())


def _is_playlist(row: Any) -> bool:
    value = _value(row, "is_playlist")
    return bool(value) if value is not None else _optional_int(_value(row, "Attribute")) == 0


def _file_type(value: Any) -> str | None:
    return FILE_TYPES.get(_optional_int(value) or 0)


def _bpm(value: Any) -> float | None:
    number = _optional_float(value)
    if number is None:
        return None
    return number / 100 if number > 1000 else number


def _msec(value: Any) -> float:
    number = _optional_float(value) or 0.0
    return number / 1000.0


def _optional_int(value: Any) -> int | None:
    return None if value in (None, "") else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value in (None, "") else float(value)


def _optional_str(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _bool_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)
