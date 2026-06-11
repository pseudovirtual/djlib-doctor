from __future__ import annotations


DEFAULT_BAD_PATH_MARKERS = (
    "trash",
    "staging",
    "temp",
    "quarantine",
    "bad-folder",
    "rejects",
    "do-not-use",
    "inactive",
)


def find_bad_path_marker(path: str, markers: tuple[str, ...] = DEFAULT_BAD_PATH_MARKERS) -> str:
    parts = _path_parts(path)
    marker_set = {_normalize_part(marker) for marker in markers if marker}
    for part in parts:
        if part in marker_set:
            return part
    return ""


def _path_parts(path: str) -> tuple[str, ...]:
    normalized = path.replace("\\", "/").lower()
    return tuple(_normalize_part(part) for part in normalized.split("/") if _normalize_part(part))


def _normalize_part(part: str) -> str:
    return part.strip().strip(":")
