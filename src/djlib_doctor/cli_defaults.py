from __future__ import annotations

from pathlib import Path

from .config import default_config, load_config
from .detect import detect_libraries


def resolve_rekordbox_xml(
    xml: Path | None, config_path: Path | None, home: Path | None, volumes: list[Path] | None
) -> Path:
    if xml is not None:
        return xml
    config = load_config(config_path) if config_path else default_config()
    if config["primary"] != "rekordbox":
        raise ValueError("verify currently supports Rekordbox XML; configured primary is serato")
    if config["rekordbox_xml"]:
        return Path(config["rekordbox_xml"])
    report = detect_libraries(home, tuple(volumes) if volumes is not None else None)
    for item in report["findings"]:
        if item["platform"] == "rekordbox" and item["kind"] == "xml_export":
            return Path(item["path"])
    raise ValueError("No Rekordbox XML path supplied, configured, or detected. Pass xml or set config rekordbox_xml.")


def resolve_port_rekordbox_xml(
    xml: Path | None, config_path: Path | None, home: Path | None, volumes: list[Path] | None
) -> Path:
    if xml is not None:
        return xml
    config = load_config(config_path) if config_path else default_config()
    if config["rekordbox_xml"]:
        return Path(config["rekordbox_xml"])
    report = detect_libraries(home, tuple(volumes) if volumes is not None else None)
    path = _first_path(report, "rekordbox", "xml_export")
    if path is not None:
        return path
    raise ValueError(
        "No Rekordbox XML path supplied, configured, or detected. Pass --rekordbox-xml or set config rekordbox_xml."
    )


def resolve_port_serato_library_dir(
    library_dir: Path | None, config_path: Path | None, home: Path | None, volumes: list[Path] | None
) -> Path:
    if library_dir is not None:
        return library_dir
    config = load_config(config_path) if config_path else default_config()
    if config["serato_library_dir"]:
        return Path(config["serato_library_dir"])
    report = detect_libraries(home, tuple(volumes) if volumes is not None else None)
    root_sqlite = _first_path(report, "serato", "root_sqlite")
    if root_sqlite is not None:
        return root_sqlite.parent
    music_dir = _first_path(report, "serato", "music_dir")
    if music_dir is not None:
        return music_dir
    raise ValueError(
        "No Serato library path supplied, configured, or detected. Pass --serato-library-dir or set config "
        "serato_library_dir."
    )


def resolve_port_collection_root(
    collection_root: Path | None, config_path: Path | None, home: Path | None, volumes: list[Path] | None
) -> Path:
    if collection_root is not None:
        return collection_root
    config = load_config(config_path) if config_path else default_config()
    if config["music_root"]:
        return Path(config["music_root"])
    report = detect_libraries(home, tuple(volumes) if volumes is not None else None)
    music_dir = _first_path(report, "serato", "music_dir")
    if music_dir is not None:
        return music_dir.parent
    raise ValueError(
        "No collection root supplied, configured, or detected. Pass --collection-root or set config music_root."
    )


def _first_path(report: dict[str, object], platform: str, kind: str) -> Path | None:
    for item in report["findings"]:
        if item["platform"] == platform and item["kind"] == kind:
            return Path(item["path"])
    return None
