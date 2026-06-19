from __future__ import annotations

from pathlib import Path, PurePath
from typing import Any

from .io_utils import read_json, write_json
from .path_utils import path_to_posix_string

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
    rekordbox_xml: PurePath | None = None,
    serato_library_dir: PurePath | None = None,
    serato_music_dir: PurePath | None = None,
    music_root: PurePath | None = None,
    crate_prefix: str = "RB - ",
    primary: str = "rekordbox",
    rekordbox_db: PurePath | None = None,
) -> dict[str, Any]:
    _validate_primary(primary)
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "primary": primary,
        "rekordbox_xml": _path(rekordbox_xml),
        "rekordbox_db": _path(rekordbox_db),
        "serato_library_dir": _path(serato_library_dir),
        "serato_music_dir": _path(serato_music_dir),
        "music_root": _path(music_root),
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


def _path(path: PurePath | None) -> str:
    return path_to_posix_string(path) if path else ""
