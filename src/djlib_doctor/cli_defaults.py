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
