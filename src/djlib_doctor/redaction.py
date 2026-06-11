from __future__ import annotations

from pathlib import Path


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
    if text.startswith("file://localhost/"):
        return f"file://localhost{redact_path(text.removeprefix('file://localhost'))}"
    if text.startswith("file:///"):
        return f"file:///{redact_path(text.removeprefix('file:///'))}"
    return redact_path(text)


def redact_text_path(text: str, original_path: str | Path | None) -> str:
    original = str(original_path or "")
    if not original:
        return text
    return text.replace(original, redact_path(original))
