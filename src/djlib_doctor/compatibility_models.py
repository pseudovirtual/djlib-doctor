from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class CompatibilitySeverity(str, Enum):
    FAILURE = "failure"
    WARNING = "warning"


@dataclass(frozen=True)
class AudioProbe:
    path: str
    extension: str
    codec: str
    sample_rate_hz: int | None = None
    bit_depth: int | None = None
    bit_rate_kbps: int | None = None
    duration_seconds: float | None = None
    probe_ok: bool = True

    @classmethod
    def from_dict(cls, row: dict[str, str]) -> "AudioProbe":
        path = row.get("path", "")
        return cls(
            path=path,
            extension=(row.get("extension") or Path(path).suffix).lower(),
            codec=(row.get("codec") or "").lower(),
            sample_rate_hz=_int_or_none(row.get("sample_rate_hz")),
            bit_depth=_int_or_none(row.get("bit_depth")),
            bit_rate_kbps=_int_or_none(row.get("bit_rate_kbps")),
            duration_seconds=_float_or_none(row.get("duration_seconds")),
            probe_ok=_bool_from_text(row.get("probe_ok", "yes")),
        )


@dataclass(frozen=True)
class AudioCompatibilityProfile:
    name: str
    description: str
    allowed_extensions: tuple[str, ...]
    allowed_codecs: tuple[str, ...]
    max_sample_rate_hz: int
    max_bit_depth: int
    warn_below_bit_rate_kbps: int = 128


@dataclass(frozen=True)
class CompatibilityIssue:
    code: str
    severity: CompatibilitySeverity
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "severity": self.severity.value, "message": self.message}


@dataclass(frozen=True)
class CompatibilityResult:
    probe: AudioProbe
    profile: AudioCompatibilityProfile
    issues: tuple[CompatibilityIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity is CompatibilitySeverity.FAILURE for issue in self.issues)

    @property
    def warnings_only(self) -> bool:
        return bool(self.issues) and self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.probe.path,
            "profile": self.profile.name,
            "status": "pass" if self.passed else "fail",
            "probe": {
                "extension": self.probe.extension,
                "codec": self.probe.codec,
                "sample_rate_hz": self.probe.sample_rate_hz,
                "bit_depth": self.probe.bit_depth,
                "bit_rate_kbps": self.probe.bit_rate_kbps,
                "duration_seconds": self.probe.duration_seconds,
                "probe_ok": self.probe.probe_ok,
            },
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _int_or_none(value: str | None) -> int | None:
    try:
        return None if value in (None, "") else int(value)
    except ValueError:
        return None


def _float_or_none(value: str | None) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except ValueError:
        return None


def _bool_from_text(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "n", "failed", "fail"}
