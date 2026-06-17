from __future__ import annotations

from pathlib import Path

from .rekordbox_uri import LOCALHOST_PREFIX, file_url_to_path

REDACTED_ROOT = "<redacted>"


def redact_path(value: str | Path | None) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    name = Path(text).name
    return f"{REDACTED_ROOT}/{name}" if name else REDACTED_ROOT


def redact_uri_or_path(value: str | Path | None) -> str:
    text = str(value or "")
    if not text:
        return ""
    file_path = file_url_to_path(text)
    if file_path is not None and text.lower().startswith(LOCALHOST_PREFIX + "/"):
        return f"{LOCALHOST_PREFIX}{redact_path(file_path)}"
    if text.startswith("file:///"):
        return f"file:///{redact_path(text.removeprefix('file:///'))}"
    return redact_path(text)


def redact_text_path(text: str, original_path: str | Path | None) -> str:
    original = str(original_path or "")
    if not original:
        return text
    return text.replace(original, redact_path(original))
