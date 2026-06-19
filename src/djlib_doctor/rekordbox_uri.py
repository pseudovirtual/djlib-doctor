from __future__ import annotations

from pathlib import Path, PurePath
from urllib.parse import quote, unquote, urlparse

from .path_utils import path_to_posix_string

LOCALHOST_PREFIX = "file://localhost"


def path_to_file_url(path: str | PurePath) -> str:
    value = path_to_posix_string(path)
    if not value.startswith(("/", "//")):
        value = "/" + value
    return LOCALHOST_PREFIX + quote(value, safe="/:")


def file_url_to_path(value: str) -> Path | None:
    lowered = value.lower()
    if lowered.startswith(LOCALHOST_PREFIX) and not lowered.startswith(LOCALHOST_PREFIX + "/"):
        return None
    parsed = urlparse(value)
    if parsed.scheme.lower() != "file":
        return None
    host = parsed.netloc
    if host and host.lower() != "localhost":
        decoded = f"//{host}{unquote(parsed.path)}"
    else:
        decoded = unquote(parsed.path)
    decoded = decoded.replace("\\", "/")
    if _has_leading_windows_drive_slash(decoded):
        decoded = decoded[1:]
    return Path(decoded) if decoded else None


def is_file_url(value: str) -> bool:
    return file_url_to_path(value) is not None


def _has_leading_windows_drive_slash(value: str) -> bool:
    return len(value) >= 4 and value[0] == "/" and value[2] == ":" and value[1].isalpha() and value[3] == "/"
