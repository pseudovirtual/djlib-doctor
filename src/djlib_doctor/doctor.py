from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .config import load_config
from .detect import detect_libraries
from .rekordbox_db_import import CONTENT_TABLE, REQUIRED_COLUMNS
from .rekordbox_xml import parse_rekordbox_xml
from .serato_database_v2 import read_serato_database_v2
from .serato_sqlite import inspect_serato_root_sqlite
from .sqlite_utils import quote_identifier, table_columns
from .verify import verify_library

DOCTOR_SCHEMA_VERSION = "1.0"


def build_doctor_report(
    home: Path | None = None, volumes: tuple[Path, ...] | None = None, config_path: Path | None = None
) -> dict[str, Any]:
    detection = _with_config_findings(detect_libraries(home, volumes), config_path)
    checkable = {"xml_export", "master_db", "root_sqlite", "database_v2"}
    checks = [_check_finding(item) for item in detection["findings"] if item["kind"] in checkable]
    return {
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "detection": detection,
        "checks": checks,
        "punch_list": _punch_list(detection, checks),
    }


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
    if item["platform"] == "rekordbox" and item["kind"] == "master_db":
        return _check_rekordbox_db(path)
    if item["platform"] == "serato" and item["kind"] == "root_sqlite":
        return _check_serato_root(path)
    if item["platform"] == "serato" and item["kind"] == "database_v2":
        return _check_serato_database_v2(path)
    raise ValueError(f"Unsupported doctor finding: {item}")


def _check_rekordbox_xml(path: Path) -> dict[str, Any]:
    try:
        report = verify_library(parse_rekordbox_xml(path), check_files=False, source_path=str(path))
        return {
            "label": "Rekordbox XML",
            "path": str(path),
            "status": "PASS" if report.passed else "FAIL",
            "summary": report.to_dict()["counts"],
        }
    except (ET.ParseError, OSError, ValueError) as exc:
        return {"label": "Rekordbox XML", "path": str(path), "status": "FAIL", "error": str(exc)}


def _check_rekordbox_db(path: Path) -> dict[str, Any]:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            columns = table_columns(conn, CONTENT_TABLE)
            missing = [column for column in REQUIRED_COLUMNS if column not in columns]
            if missing:
                raise ValueError("Unsupported Rekordbox DB schema; missing " + ", ".join(missing))
            count = conn.execute(f"SELECT COUNT(*) FROM {quote_identifier(CONTENT_TABLE)}").fetchone()[0]
        finally:
            conn.close()
        return {
            "label": "Rekordbox DB",
            "path": str(path),
            "status": "PASS",
            "summary": {"tracks": int(count), "content_table": CONTENT_TABLE},
        }
    except sqlite3.DatabaseError as exc:
        return {
            "label": "Rekordbox DB",
            "path": str(path),
            "status": "FAIL",
            "error": _unsupported_rekordbox_db_message(path, exc),
        }
    except (OSError, ValueError) as exc:
        return {"label": "Rekordbox DB", "path": str(path), "status": "FAIL", "error": str(exc)}


def _check_serato_root(path: Path) -> dict[str, Any]:
    try:
        inspection = inspect_serato_root_sqlite(path)
        return {
            "label": "Serato root.sqlite",
            "path": str(path),
            "status": "PASS",
            "summary": inspection.to_dict()["summary"],
        }
    except (OSError, ValueError) as exc:
        return {"label": "Serato root.sqlite", "path": str(path), "status": "FAIL", "error": str(exc)}


def _check_serato_database_v2(path: Path) -> dict[str, Any]:
    try:
        database = read_serato_database_v2(path)
        return {
            "label": "Serato database V2",
            "path": str(path),
            "status": "PASS",
            "summary": {"tracks": len(database.tracks), "version": database.version},
        }
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return {"label": "Serato database V2", "path": str(path), "status": "FAIL", "error": str(exc)}


def _check_line(check: dict[str, Any]) -> str:
    suffix = f" ({check['error']})" if check.get("error") else ""
    return f"- {check['label']}: {check['status']} {check['path']}{suffix}"


def _with_config_findings(detection: dict[str, Any], config_path: Path | None) -> dict[str, Any]:
    if config_path is None:
        return detection
    findings = detection["findings"] + _config_findings(load_config(config_path))
    merged = {**detection, "findings": _unique_findings(findings)}
    merged["summary"] = {
        platform: sum(1 for item in merged["findings"] if item["platform"] == platform)
        for platform in ("rekordbox", "serato")
    }
    return merged


def _config_findings(config: dict[str, Any]) -> list[dict[str, str]]:
    findings = []
    if config["rekordbox_xml"]:
        findings.append(_finding("rekordbox", "xml_export", config["rekordbox_xml"]))
    if config["rekordbox_db"]:
        findings.append(_finding("rekordbox", "master_db", config["rekordbox_db"]))
    if config["serato_music_dir"]:
        serato_dir = Path(config["serato_music_dir"])
        findings.append(_finding("serato", "music_dir", str(serato_dir)))
        findings.append(_finding("serato", "database_v2", str(serato_dir / "database V2")))
    if config["serato_library_dir"]:
        findings.append(_finding("serato", "root_sqlite", str(Path(config["serato_library_dir"]) / "root.sqlite")))
    return findings


def _unique_findings(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    unique = []
    seen = set()
    for item in findings:
        key = (item["platform"], item["kind"], item["path"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _finding(platform: str, kind: str, path: str) -> dict[str, str]:
    return {"platform": platform, "kind": kind, "path": path}


def _unsupported_rekordbox_db_message(path: Path, exc: sqlite3.DatabaseError) -> str:
    return (
        f"Unsupported Rekordbox DB format: {path}. Modern encrypted SQLCipher "
        "Rekordbox databases are not supported by doctor yet; use a Rekordbox XML export "
        f"or install a future Rekordbox DB backend. SQLite error: {exc}"
    )


def _punch_list(detection: dict[str, Any], checks: list[dict[str, Any]]) -> list[str]:
    if not detection["findings"]:
        return ["Run `djlib-doctor detect` after configuring paths or connecting local drives."]
    items = []
    for check in checks:
        if check["label"] == "Rekordbox XML":
            items.append(
                f"Snapshot Rekordbox export: djlib-doctor snapshot --rekordbox-xml {check['path']} --out run/snapshot --no-file-check"
            )
        if check["label"] == "Serato root.sqlite":
            items.append(
                f"Inspect Serato: djlib-doctor inspect serato --library-dir {Path(check['path']).parent} --out run/inspect-serato"
            )
        if check["label"] == "Serato database V2":
            items.append(f"Review Serato database V2 tracks in doctor output: {check['path']}")
    items.append(
        "Configure primary sync paths: djlib-doctor config init --out run/djlib-doctor.json --primary rekordbox"
    )
    return items
