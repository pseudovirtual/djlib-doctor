from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .serato_tlv import decode_text, parse_records, record, text

CRATE_VERSION = "1.0/Serato ScratchLive Crate"


@dataclass(frozen=True)
class SeratoCrate:
    version: str
    tracks: tuple[str, ...]


def write_serato_crate(path: Path, portable_ids: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [record("vrsn", text(CRATE_VERSION))]
    for portable_id in portable_ids:
        records.append(record("otrk", record("ptrk", text(portable_id))))
    path.write_bytes(b"".join(records))


def read_serato_crate(path: Path) -> SeratoCrate:
    records = parse_records(path.read_bytes())
    version = ""
    tracks = []
    for tag, payload in records:
        if tag == "vrsn":
            version = decode_text(payload)
        elif tag == "otrk":
            for child_tag, child_payload in parse_records(payload):
                if child_tag == "ptrk":
                    tracks.append(decode_text(child_payload))
    return SeratoCrate(version=version, tracks=tuple(tracks))


def safe_crate_filename(name: str) -> str:
    safe = name.replace("/", " - ").replace("\\", " - ").replace(":", " - ")
    return " ".join(safe.split()).strip() or "Migrated Crate"
