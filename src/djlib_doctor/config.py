from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json

CONFIG_SCHEMA_VERSION = "1.0"
PRIMARY_VALUES = {"rekordbox", "serato"}
CONFIG_KEYS = {
    "schema_version",
    "primary",
    "rekordbox_xml",
    "rekordbox_db",
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
    primary: str = "rekordbox",
    rekordbox_db: Path | None = None,
) -> dict[str, Any]:
    _validate_primary(primary)
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "primary": primary,
        "rekordbox_xml": str(rekordbox_xml) if rekordbox_xml else "",
        "rekordbox_db": str(rekordbox_db) if rekordbox_db else "",
        "serato_library_dir": str(serato_library_dir) if serato_library_dir else "",
        "serato_music_dir": str(serato_music_dir) if serato_music_dir else "",
        "music_root": str(music_root) if music_root else "",
        "crate_prefix": crate_prefix,
    }


def load_config(path: Path) -> dict[str, Any]:
    data = read_json(path)
    unknown = sorted(set(data) - CONFIG_KEYS)
    if unknown:
        raise ValueError(f"Unknown config keys: {', '.join(unknown)}")
    merged = default_config()
    merged.update(data)
    _validate_primary(merged["primary"])
    return merged


def write_config(path: Path, config: dict[str, Any]) -> None:
    unknown = sorted(set(config) - CONFIG_KEYS)
    if unknown:
        raise ValueError(f"Unknown config keys: {', '.join(unknown)}")
    if "primary" in config:
        _validate_primary(config["primary"])
    write_json(path, config)


def _validate_primary(primary: Any) -> None:
    if primary not in PRIMARY_VALUES:
        raise ValueError("Config primary must be 'rekordbox' or 'serato'")
