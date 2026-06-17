from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

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

    raw_lowered = raw_location.lower()
    if raw_lowered.startswith("file://localhost/"):
        return LocationKind.LOCAL_FILE, Path(unquote(raw_location[len("file://localhost") :]))

    if raw_lowered.startswith("file:///"):
        parsed = urlparse(raw_location)
        return LocationKind.LOCAL_FILE, Path(unquote(parsed.path))

    decoded = unquote(raw_location)
    lowered = decoded.lower()
    if decoded.startswith("/"):
        return LocationKind.LOCAL_FILE, Path(decoded)

    if any(marker in lowered for marker in STREAMING_MARKERS):
        return LocationKind.STREAMING_PLACEHOLDER, None

    return LocationKind.UNKNOWN, None
