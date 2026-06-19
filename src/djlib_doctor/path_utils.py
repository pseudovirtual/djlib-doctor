from __future__ import annotations

from pathlib import PurePath


def path_to_posix_string(path: str | PurePath) -> str:
    return path.as_posix() if isinstance(path, PurePath) else str(path).replace("\\", "/")
