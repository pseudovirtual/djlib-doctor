from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from .detect import detect_libraries
from .rekordbox_xml import parse_rekordbox_xml
from .serato_sqlite import inspect_serato_root_sqlite
from .verify import verify_library


def build_doctor_report(home: Path | None = None, volumes: tuple[Path, ...] | None = None) -> dict[str, Any]:
    detection = detect_libraries(home, volumes)
    checks = [_check_finding(item) for item in detection["findings"] if item["kind"] in {"xml_export", "root_sqlite"}]
    return {"detection": detection, "checks": checks, "punch_list": _punch_list(detection, checks)}


def render_doctor_report(report: dict[str, Any]) -> str:
    lines = ["djlib-doctor doctor"]
    if not report["detection"]["findings"]:
        lines.append("No Rekordbox or Serato libraries found.")
    else:
        lines.append("Detected libraries:")
        lines.extend(f"- {item['platform']} {item['kind']}: {item['path']}" for item in report["detection"]["findings"])
    if report["checks"]:
        lines.append("")
        lines.append("Checks:")
        lines.extend(_check_line(check) for check in report["checks"])
    lines.append("")
    lines.append("Punch list:")
    lines.extend(f"- {item}" for item in report["punch_list"])
    return "\n".join(lines)


def _check_finding(item: dict[str, str]) -> dict[str, Any]:
    path = Path(item["path"])
    if item["platform"] == "rekordbox" and item["kind"] == "xml_export":
        return _check_rekordbox_xml(path)
    if item["platform"] == "serato" and item["kind"] == "root_sqlite":
        return _check_serato_root(path)
    raise ValueError(f"Unsupported doctor finding: {item}")


def _check_rekordbox_xml(path: Path) -> dict[str, Any]:
    try:
        report = verify_library(parse_rekordbox_xml(path), check_files=False, source_path=str(path))
        return {"label": "Rekordbox XML", "path": str(path), "status": "PASS" if report.passed else "FAIL", "summary": report.to_dict()["counts"]}
    except (ET.ParseError, OSError, ValueError) as exc:
        return {"label": "Rekordbox XML", "path": str(path), "status": "FAIL", "error": str(exc)}


def _check_serato_root(path: Path) -> dict[str, Any]:
    try:
        inspection = inspect_serato_root_sqlite(path)
        return {"label": "Serato root.sqlite", "path": str(path), "status": "PASS", "summary": inspection.to_dict()["summary"]}
    except (OSError, ValueError) as exc:
        return {"label": "Serato root.sqlite", "path": str(path), "status": "FAIL", "error": str(exc)}


def _check_line(check: dict[str, Any]) -> str:
    suffix = f" ({check['error']})" if check.get("error") else ""
    return f"- {check['label']}: {check['status']} {check['path']}{suffix}"


def _punch_list(detection: dict[str, Any], checks: list[dict[str, Any]]) -> list[str]:
    if not detection["findings"]:
        return ["Run `djlib-doctor detect` after configuring paths or connecting local drives."]
    items = []
    for check in checks:
        if check["label"] == "Rekordbox XML":
            items.append(f"Snapshot Rekordbox export: djlib-doctor snapshot --rekordbox-xml {check['path']} --out run/snapshot --no-file-check")
        if check["label"] == "Serato root.sqlite":
            items.append(f"Inspect Serato: djlib-doctor inspect serato --library-dir {Path(check['path']).parent} --out run/inspect-serato")
    items.append("Configure primary sync paths: djlib-doctor config init --out run/djlib-doctor.json --primary rekordbox")
    return items
