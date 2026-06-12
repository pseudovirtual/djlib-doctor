from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONFIG_SCHEMA_VERSION = "1.0"
CONFIG_KEYS = {
    "schema_version",
    "rekordbox_xml",
    "serato_library_dir",
    "serato_music_dir",
    "music_root",
    "crate_prefix",
}


def default_config(
    rekordbox_xml: Path | None = None,
    serato_library_dir: Path | None = None,
    serato_music_dir: Path | None = None,
    music_root: Path | None = None,
    crate_prefix: str = "RB - ",
) -> dict[str, Any]:
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "rekordbox_xml": str(rekordbox_xml) if rekordbox_xml else "",
        "serato_library_dir": str(serato_library_dir) if serato_library_dir else "",
        "serato_music_dir": str(serato_music_dir) if serato_music_dir else "",
        "music_root": str(music_root) if music_root else "",
        "crate_prefix": crate_prefix,
    }


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    unknown = sorted(set(data) - CONFIG_KEYS)
    if unknown:
        raise ValueError(f"Unknown config keys: {', '.join(unknown)}")
    merged = default_config()
    merged.update(data)
    return merged


def write_config(path: Path, config: dict[str, Any]) -> None:
    unknown = sorted(set(config) - CONFIG_KEYS)
    if unknown:
        raise ValueError(f"Unknown config keys: {', '.join(unknown)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
