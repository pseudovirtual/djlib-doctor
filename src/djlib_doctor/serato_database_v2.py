from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .serato_tlv import decode_text, parse_records

TEXT_FIELD_TAGS = {"pfil", "tsng", "tart", "talb", "tgen", "tkey", "tbpm"}


@dataclass(frozen=True)
class SeratoDatabaseV2Track:
    path: str
    title: str = ""
    artist: str = ""
    album: str = ""
    genre: str = ""
    key: str = ""
    bpm: float | None = None


@dataclass(frozen=True)
class SeratoDatabaseV2:
    version: str
    tracks: tuple[SeratoDatabaseV2Track, ...]

    @property
    def track_paths(self) -> tuple[str, ...]:
        return tuple(track.path for track in self.tracks)


def read_serato_database_v2(path: Path) -> SeratoDatabaseV2:
    records = parse_records(path.read_bytes())
    version = ""
    tracks = []
    for tag, payload in records:
        if tag == "vrsn":
            version = decode_text(payload)
        elif tag == "otrk":
            track = _track(payload)
            if track is not None:
                tracks.append(track)
    return SeratoDatabaseV2(version, tuple(tracks))


def _track(payload: bytes) -> SeratoDatabaseV2Track | None:
    fields = _fields(payload)
    path = fields.get("pfil", "")
    if not path:
        return None
    return SeratoDatabaseV2Track(
        path=path,
        title=fields.get("tsng", ""),
        artist=fields.get("tart", ""),
        album=fields.get("talb", ""),
        genre=fields.get("tgen", ""),
        key=fields.get("tkey", ""),
        bpm=_optional_float(fields.get("tbpm")),
    )


def _fields(payload: bytes) -> dict[str, str]:
    return {tag: decode_text(value) for tag, value in _field_records(payload) if tag in TEXT_FIELD_TAGS}


def _field_records(payload: bytes) -> tuple[tuple[str, bytes], ...]:
    try:
        children = parse_records(payload)
    except (UnicodeDecodeError, ValueError):
        return ()
    records = []
    for tag, value in children:
        nested = _field_records(value)
        if nested:
            records.extend(nested)
        else:
            records.append((tag, value))
    return tuple(records)


def _optional_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
