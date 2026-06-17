from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import render_json


DETECT_SCHEMA_VERSION = "1.0"


def detect_libraries(home: Path | None = None, volumes: tuple[Path, ...] | None = None) -> dict[str, Any]:
    home = home or Path.home()
    volume_roots = volumes if volumes is not None else _default_volumes()
    findings = _rekordbox_findings(home) + _serato_findings(home, volume_roots)
    return {
        "schema_version": DETECT_SCHEMA_VERSION,
        "home": str(home),
        "volumes": [str(path) for path in volume_roots],
        "summary": {
            "rekordbox": sum(1 for item in findings if item["platform"] == "rekordbox"),
            "serato": sum(1 for item in findings if item["platform"] == "serato"),
        },
        "findings": findings,
    }


def render_detect_text(report: dict[str, Any]) -> str:
    lines = ["djlib-doctor detect"]
    if not report["findings"]:
        lines.append("No Rekordbox or Serato library paths found.")
        return "\n".join(lines)
    for item in report["findings"]:
        lines.append(f"- {item['platform']} {item['kind']}: {item['path']}")
    return "\n".join(lines)


def render_detect_json(report: dict[str, Any], pretty: bool = False) -> str:
    return render_json(report, pretty=pretty)


def _rekordbox_findings(home: Path) -> list[dict[str, str]]:
    candidates = (
        ("master_db", home / "Library" / "Pioneer" / "rekordbox" / "master.db"),
        ("master_db", home / "Library" / "Application Support" / "Pioneer" / "rekordbox" / "master.db"),
        ("xml_export", home / "Desktop" / "rekordbox.xml"),
        ("xml_export", home / "Desktop" / "rekordbox-export.xml"),
        ("xml_export", home / "Documents" / "rekordbox.xml"),
        ("xml_export", home / "Documents" / "rekordbox-export.xml"),
    )
    return [_finding("rekordbox", kind, path) for kind, path in candidates if path.exists()]


def _serato_findings(home: Path, volumes: tuple[Path, ...]) -> list[dict[str, str]]:
    serato_dirs = _existing_serato_dirs((home / "Music" / "_Serato_", home / "_Serato_"))
    for volume in volumes:
        serato_dirs.extend(_existing_serato_dirs((volume / "_Serato_", volume / "Music" / "_Serato_")))
    findings: list[dict[str, str]] = []
    seen: set[Path] = set()
    for serato_dir in serato_dirs:
        if serato_dir in seen:
            continue
        seen.add(serato_dir)
        findings.append(_finding("serato", "music_dir", serato_dir))
        for kind, child in (
            ("database_v2", serato_dir / "database V2"),
            ("subcrates", serato_dir / "Subcrates"),
            ("root_sqlite", serato_dir / "root.sqlite"),
        ):
            if child.exists():
                findings.append(_finding("serato", kind, child))
    return findings


def _default_volumes() -> tuple[Path, ...]:
    root = Path("/Volumes")
    if not root.exists():
        return ()
    return tuple(path for path in root.iterdir() if path.is_dir())


def _existing_serato_dirs(paths: tuple[Path, ...]) -> list[Path]:
    return [path for path in paths if path.is_dir()]


def _finding(platform: str, kind: str, path: Path) -> dict[str, str]:
    return {"platform": platform, "kind": kind, "path": str(path)}
