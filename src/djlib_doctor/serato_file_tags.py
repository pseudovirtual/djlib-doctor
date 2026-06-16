from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Callable

from .serato_markers import parse_markers2_payload

MARKERS2_GEOB_KEY = "GEOB:Serato Markers2"
MARKERS2_DESC = "Serato Markers2"
SERATO_MARKERS2_VERSION = b"\x01\x01"


def read_serato_markers2_file_tags(path: Path, file_loader: Callable[[Path], Any] | None = None) -> tuple[dict[str, Any], ...]:
    if file_loader is None and not path.exists():
        return ()
    audio = _load_audio(path, file_loader)
    data = _markers2_data(getattr(audio, "tags", None))
    return parse_markers2_payload(decode_serato_geob_payload(data)) if data else ()


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


def _markers2_data(tags: Any) -> bytes | None:
    if not tags:
        return None
    frame = _tag_frame(tags, MARKERS2_GEOB_KEY)
    if frame is None and hasattr(tags, "values"):
        frame = next((item for item in tags.values() if getattr(item, "desc", "") == MARKERS2_DESC), None)
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
