from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Callable

from .serato_beatgrid import parse_beatgrid_payload
from .serato_markers import parse_markers2_payload

MARKERS2_GEOB_KEY = "GEOB:Serato Markers2"
MARKERS2_DESC = "Serato Markers2"
BEATGRID_GEOB_KEY = "GEOB:Serato BeatGrid"
BEATGRID_DESC = "Serato BeatGrid"
SERATO_MARKERS2_VERSION = b"\x01\x01"


def read_serato_markers2_file_tags(path: Path, file_loader: Callable[[Path], Any] | None = None) -> tuple[dict[str, Any], ...]:
    if file_loader is None and not path.exists():
        return ()
    audio = _load_audio(path, file_loader)
    data = _geob_data(getattr(audio, "tags", None), MARKERS2_GEOB_KEY, MARKERS2_DESC)
    return parse_markers2_payload(decode_serato_geob_payload(data)) if data else ()


def read_serato_file_tags(path: Path, file_loader: Callable[[Path], Any] | None = None) -> dict[str, tuple[dict[str, Any], ...]]:
    if file_loader is None and not path.exists():
        return {"markers2": (), "beatgrid": ()}
    audio = _load_audio(path, file_loader)
    tags = getattr(audio, "tags", None)
    markers2 = _geob_data(tags, MARKERS2_GEOB_KEY, MARKERS2_DESC)
    beatgrid = _geob_data(tags, BEATGRID_GEOB_KEY, BEATGRID_DESC)
    return {
        "markers2": parse_markers2_payload(decode_serato_geob_payload(markers2)) if markers2 else (),
        "beatgrid": parse_beatgrid_payload(decode_serato_geob_payload(beatgrid)) if beatgrid else (),
    }


def decode_serato_geob_payload(data: bytes) -> bytes:
    if not data or _looks_decoded(data):
        return data
    if not data.startswith(SERATO_MARKERS2_VERSION):
        return data
    encoded = data[2:].split(b"\x00", 1)[0].replace(b"\n", b"")
    if not encoded:
        return b""
    padding = b"A==" if len(encoded) % 4 == 1 else b"=" * (-len(encoded) % 4)
    return base64.b64decode(encoded + padding)


def _load_audio(path: Path, file_loader: Callable[[Path], Any] | None) -> Any:
    if file_loader is not None:
        return file_loader(path)
    try:
        from mutagen import File
    except ImportError as exc:
        raise ImportError("Install djlib-doctor[audio-tags] to read Serato audio file tags") from exc
    return File(path)


def _geob_data(tags: Any, key: str, desc: str) -> bytes | None:
    if not tags:
        return None
    frame = _tag_frame(tags, key)
    if frame is None and hasattr(tags, "values"):
        frame = next((item for item in tags.values() if getattr(item, "desc", "") == desc), None)
    return getattr(frame, "data", None)


def _tag_frame(tags: Any, key: str) -> Any:
    if hasattr(tags, "get"):
        return tags.get(key)
    try:
        return tags[key]
    except (KeyError, TypeError):
        return None


def _looks_decoded(data: bytes) -> bool:
    return data.startswith(SERATO_MARKERS2_VERSION) and data[2:6] in {b"CUE\x00", b"LOOP", b"COLO", b"BPML", b"FLIP"}
