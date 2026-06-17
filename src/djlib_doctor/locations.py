from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from .rekordbox_uri import file_url_to_path

STREAMING_MARKERS = (
    "soundcloud:",
    "spotify:",
    "beatport:",
    "beatsource:",
    "tidal:",
)


class LocationKind(str, Enum):
    LOCAL_FILE = "local_file"
    STREAMING_PLACEHOLDER = "streaming_placeholder"
    UNKNOWN = "unknown"


def parse_location(raw_location: Optional[str]) -> tuple[LocationKind, Optional[Path]]:
    if not raw_location:
        return LocationKind.UNKNOWN, None

    file_path = file_url_to_path(raw_location)
    if file_path is not None:
        return LocationKind.LOCAL_FILE, file_path

    decoded = unquote(raw_location)
    lowered = decoded.lower()
    if decoded.startswith("/"):
        return LocationKind.LOCAL_FILE, Path(decoded)

    if any(marker in lowered for marker in STREAMING_MARKERS):
        return LocationKind.STREAMING_PLACEHOLDER, None

    return LocationKind.UNKNOWN, None
