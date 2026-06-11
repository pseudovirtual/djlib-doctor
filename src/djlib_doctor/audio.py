from __future__ import annotations

from pathlib import Path
from typing import Iterable


AUDIO_EXTENSIONS = {
    ".aac",
    ".aif",
    ".aiff",
    ".alac",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
}


def iter_audio_files(root: Path) -> Iterable[Path]:
    if not root.exists() or not root.is_dir():
        return
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            yield path
