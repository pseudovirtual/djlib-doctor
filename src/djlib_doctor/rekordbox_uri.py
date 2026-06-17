from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, unquote, urlparse

LOCALHOST_PREFIX = "file://localhost"


def path_to_file_url(path: str | Path) -> str:
    return LOCALHOST_PREFIX + quote(str(path))


def file_url_to_path(value: str) -> Path | None:
    lowered = value.lower()
    if lowered.startswith(LOCALHOST_PREFIX + "/"):
        return Path(unquote(value[len(LOCALHOST_PREFIX) :]))
    if lowered.startswith("file:///"):
        return Path(unquote(urlparse(value).path))
    return None


def is_file_url(value: str) -> bool:
    return file_url_to_path(value) is not None
