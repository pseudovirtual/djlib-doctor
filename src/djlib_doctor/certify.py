from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json
from .serato_crate import safe_crate_filename


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class CertificationIssue:
    severity: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CertificationReport:
    manifest_path: str
    source_platform: str
    target_platform: str
    summary: dict[str, Any]
    issues: tuple[CertificationIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "passed": self.passed,
            "manifest_path": self.manifest_path,
            "source_platform": self.source_platform,
            "target_platform": self.target_platform,
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def certify_port_manifest(path: Path) -> CertificationReport:
    manifest = read_json(path)
    issues = _manifest_issues(manifest) + _artifact_issues(path.parent, manifest)
    return CertificationReport(
        str(path),
        str(manifest.get("source_platform", "unknown")),
        str(manifest.get("target_platform", "unknown")),
        _summary(manifest),
        tuple(issues),
    )


def write_certification_report(report: CertificationReport, out: Path) -> None:
    write_json(out, report.to_dict())


def _summary(manifest: dict[str, Any]) -> dict[str, Any]:
    tracks = _tracks(manifest)
    cue_count = sum(len(track.get("cue_intents", track.get("cues", []))) for track in tracks)
    skipped = _skipped(manifest)
    warnings = manifest.get("warnings", [])
    return {
        "scope": manifest.get("scope", "unknown"),
        "transfer_mode": manifest.get("transfer_mode", "unknown"),
        "tracks": len(tracks),
        "cues": cue_count,
        "skipped": len(skipped),
        "warnings": len(warnings),
        "unsupported_tracks": sum(1 for track in tracks if track.get("unsupported")),
    }


def _tracks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if "crates" in manifest:
        return [track for crate in manifest.get("crates", []) for track in crate.get("tracks", [])]
    return list(manifest.get("tracks", []))


def _skipped(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if "crates" in manifest:
        return [row for crate in manifest.get("crates", []) for row in crate.get("skipped", [])]
    return list(manifest.get("skipped", []))


def _manifest_issues(manifest: dict[str, Any]) -> list[CertificationIssue]:
    issues = []
    if manifest.get("mode") != "dry_run_only":
        issues.append(CertificationIssue("error", "manifest.mode", "Port manifest must be dry_run_only."))
    if _skipped(manifest):
        issues.append(CertificationIssue("warning", "manifest.skipped", "Manifest contains skipped tracks."))
    if any(track.get("unsupported") for track in _tracks(manifest)):
        issues.append(CertificationIssue("warning", "manifest.unsupported", "Some tracks contain unsupported migration details."))
    return issues


def _artifact_issues(base: Path, manifest: dict[str, Any]) -> list[CertificationIssue]:
    target = manifest.get("target_platform")
    if target == "serato":
        return _serato_artifact_issues(base, manifest)
    if str(target).startswith("rekordbox"):
        return _required_files(base, ("rekordbox-preview.xml",), "rekordbox.preview")
    return [CertificationIssue("warning", "manifest.target", f"Unknown target platform: {target}")]


def _serato_artifact_issues(base: Path, manifest: dict[str, Any]) -> list[CertificationIssue]:
    crate_names = [crate.get("target_crate_name", "") for crate in manifest.get("crates", [])]
    if not crate_names:
        crate_names = [manifest.get("target_crate_name", "")]
    crate_files = tuple(f"{safe_crate_filename(name)}.crate" for name in crate_names if name)
    return _required_files(base, crate_files + ("unsupported.csv",), "serato.preview")


def _required_files(base: Path, names: tuple[str, ...], code: str) -> list[CertificationIssue]:
    return [
        CertificationIssue("error", code, f"Expected artifact is missing: {name}")
        for name in names
        if not (base / name).exists()
    ]
