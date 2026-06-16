from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .serato_tlv import decode_text, parse_records


@dataclass(frozen=True)
class SeratoDatabaseV2:
    version: str
    tracks: tuple[str, ...]


def read_serato_database_v2(path: Path) -> SeratoDatabaseV2:
    records = parse_records(path.read_bytes())
    version = ""
    tracks = []
    for tag, payload in records:
        if tag == "vrsn":
            version = decode_text(payload)
        elif tag == "otrk":
            tracks.extend(_track_paths(payload))
    return SeratoDatabaseV2(version, tuple(tracks))


def _track_paths(payload: bytes) -> tuple[str, ...]:
    tracks = []
    for child_tag, child_payload in parse_records(payload):
        if child_tag == "ptrk":
            tracks.append(decode_text(child_payload))
    return tuple(tracks)
