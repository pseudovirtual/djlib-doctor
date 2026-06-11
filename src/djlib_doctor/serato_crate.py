from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct


CRATE_VERSION = "1.0/Serato ScratchLive Crate"


@dataclass(frozen=True)
class SeratoCrate:
    version: str
    tracks: tuple[str, ...]


def write_serato_crate(path: Path, portable_ids: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [_record("vrsn", _text(CRATE_VERSION))]
    for portable_id in portable_ids:
        records.append(_record("otrk", _record("ptrk", _text(portable_id))))
    path.write_bytes(b"".join(records))


def read_serato_crate(path: Path) -> SeratoCrate:
    records = _parse_records(path.read_bytes())
    version = ""
    tracks = []
    for tag, payload in records:
        if tag == "vrsn":
            version = _decode_text(payload)
        elif tag == "otrk":
            for child_tag, child_payload in _parse_records(payload):
                if child_tag == "ptrk":
                    tracks.append(_decode_text(child_payload))
    return SeratoCrate(version=version, tracks=tuple(tracks))


def safe_crate_filename(name: str) -> str:
    safe = name.replace("/", " - ").replace("\\", " - ").replace(":", " - ")
    return " ".join(safe.split()).strip() or "Migrated Crate"


def _record(tag: str, payload: bytes) -> bytes:
    if len(tag) != 4:
        raise ValueError(f"Serato crate tags must be four characters: {tag}")
    return tag.encode("ascii") + struct.pack(">I", len(payload)) + payload


def _parse_records(data: bytes) -> tuple[tuple[str, bytes], ...]:
    records = []
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Truncated Serato crate record header")
        tag = data[offset : offset + 4].decode("ascii")
        length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        offset += 8
        payload = data[offset : offset + length]
        if len(payload) != length:
            raise ValueError(f"Truncated Serato crate record payload: {tag}")
        records.append((tag, payload))
        offset += length
    return tuple(records)


def _text(value: str) -> bytes:
    return value.encode("utf-16-be")


def _decode_text(value: bytes) -> str:
    return value.decode("utf-16-be")
