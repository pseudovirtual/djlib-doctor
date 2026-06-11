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
        extension = row.get("extension") or Path(path).suffix
        return cls(
            path=path,
            extension=extension.lower(),
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
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }


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


REKORDBOX_CONSERVATIVE_PROFILE = AudioCompatibilityProfile(
    name="rekordbox-conservative",
    description="General Rekordbox-oriented USB safety default: AAC/MP3/WAV/AIFF up to 48 kHz and 24-bit PCM.",
    allowed_extensions=(".aif", ".aiff", ".m4a", ".mp3", ".wav"),
    allowed_codecs=("aac", "mp3", "pcm_s16be", "pcm_s16le", "pcm_s24be", "pcm_s24le"),
    max_sample_rate_hz=48_000,
    max_bit_depth=24,
)

REKORDBOX_AIFF_16_PROFILE = AudioCompatibilityProfile(
    name="rekordbox-aiff-16",
    description="AIFF-only workflow with 16-bit PCM, useful when standardizing a Rekordbox library around AIFF.",
    allowed_extensions=(".aif", ".aiff"),
    allowed_codecs=("pcm_s16be", "pcm_s16le"),
    max_sample_rate_hz=48_000,
    max_bit_depth=16,
)

REKORDBOX_AIFF_24_PROFILE = AudioCompatibilityProfile(
    name="rekordbox-aiff-24",
    description="AIFF-only workflow allowing 24-bit PCM up to 48 kHz.",
    allowed_extensions=(".aif", ".aiff"),
    allowed_codecs=("pcm_s16be", "pcm_s16le", "pcm_s24be", "pcm_s24le"),
    max_sample_rate_hz=48_000,
    max_bit_depth=24,
)

WAV_16_PROFILE = AudioCompatibilityProfile(
    name="wav-16",
    description="WAV-only workflow with 16-bit PCM.",
    allowed_extensions=(".wav",),
    allowed_codecs=("pcm_s16le", "pcm_s16be"),
    max_sample_rate_hz=48_000,
    max_bit_depth=16,
)

WAV_24_PROFILE = AudioCompatibilityProfile(
    name="wav-24",
    description="WAV-only workflow allowing 24-bit PCM up to 48 kHz.",
    allowed_extensions=(".wav",),
    allowed_codecs=("pcm_s16le", "pcm_s16be", "pcm_s24le", "pcm_s24be"),
    max_sample_rate_hz=48_000,
    max_bit_depth=24,
)

BROAD_SOFTWARE_LIBRARY_PROFILE = AudioCompatibilityProfile(
    name="broad-software-library",
    description="Broad software-library review profile for DJs who intentionally keep AAC/ALAC/FLAC/MP3/WAV/AIFF files.",
    allowed_extensions=(".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"),
    allowed_codecs=("aac", "alac", "flac", "mp3", "pcm_s16be", "pcm_s16le", "pcm_s24be", "pcm_s24le"),
    max_sample_rate_hz=96_000,
    max_bit_depth=24,
)

AUDIO_COMPATIBILITY_PROFILES = {
    profile.name: profile
    for profile in (
        REKORDBOX_CONSERVATIVE_PROFILE,
        REKORDBOX_AIFF_16_PROFILE,
        REKORDBOX_AIFF_24_PROFILE,
        WAV_16_PROFILE,
        WAV_24_PROFILE,
        BROAD_SOFTWARE_LIBRARY_PROFILE,
    )
}

CONSERVATIVE_DJ_USB_PROFILE = REKORDBOX_CONSERVATIVE_PROFILE


def check_audio_compatibility(
    probe: AudioProbe,
    profile: AudioCompatibilityProfile = REKORDBOX_CONSERVATIVE_PROFILE,
) -> CompatibilityResult:
    issues: list[CompatibilityIssue] = []
    extension = probe.extension.lower()
    codec = probe.codec.lower()

    if not probe.probe_ok:
        issues.append(
            CompatibilityIssue(
                code="probe_failed",
                severity=CompatibilitySeverity.FAILURE,
                message="Audio probe did not complete; compatibility cannot be trusted.",
            )
        )

    if extension and extension not in profile.allowed_extensions:
        issues.append(
            CompatibilityIssue(
                code="unsupported_extension",
                severity=CompatibilitySeverity.FAILURE,
                message=f"Extension {extension} is outside the {profile.name} profile.",
            )
        )

    if not codec:
        issues.append(
            CompatibilityIssue(
                code="unknown_codec",
                severity=CompatibilitySeverity.WARNING,
                message="Codec is missing from probe metadata.",
            )
        )
    elif codec not in profile.allowed_codecs:
        issues.append(
            CompatibilityIssue(
                code="unsupported_codec",
                severity=CompatibilitySeverity.FAILURE,
                message=f"Codec {codec} is outside the {profile.name} profile.",
            )
        )

    if probe.sample_rate_hz is not None and probe.sample_rate_hz > profile.max_sample_rate_hz:
        issues.append(
            CompatibilityIssue(
                code="sample_rate_too_high",
                severity=CompatibilitySeverity.FAILURE,
                message=f"Sample rate {probe.sample_rate_hz} Hz exceeds {profile.max_sample_rate_hz} Hz.",
            )
        )

    if probe.bit_depth is not None and probe.bit_depth > profile.max_bit_depth:
        issues.append(
            CompatibilityIssue(
                code="bit_depth_too_high",
                severity=CompatibilitySeverity.FAILURE,
                message=f"Bit depth {probe.bit_depth} exceeds {profile.max_bit_depth}.",
            )
        )

    if probe.duration_seconds is not None and probe.duration_seconds <= 0:
        issues.append(
            CompatibilityIssue(
                code="invalid_duration",
                severity=CompatibilitySeverity.WARNING,
                message="Duration is zero or negative.",
            )
        )

    if probe.bit_rate_kbps is not None and 0 < probe.bit_rate_kbps < profile.warn_below_bit_rate_kbps:
        issues.append(
            CompatibilityIssue(
                code="low_bit_rate",
                severity=CompatibilitySeverity.WARNING,
                message=f"Bit rate {probe.bit_rate_kbps} kbps is below {profile.warn_below_bit_rate_kbps} kbps.",
            )
        )

    return CompatibilityResult(probe=probe, profile=profile, issues=tuple(issues))


def get_audio_compatibility_profile(name: str) -> AudioCompatibilityProfile:
    try:
        return AUDIO_COMPATIBILITY_PROFILES[name]
    except KeyError as exc:
        known = ", ".join(sorted(AUDIO_COMPATIBILITY_PROFILES))
        raise ValueError(f"Unknown audio compatibility profile {name!r}. Known profiles: {known}") from exc


def list_audio_compatibility_profiles() -> tuple[AudioCompatibilityProfile, ...]:
    return tuple(AUDIO_COMPATIBILITY_PROFILES[name] for name in sorted(AUDIO_COMPATIBILITY_PROFILES))


def customize_audio_compatibility_profile(
    profile: AudioCompatibilityProfile,
    allowed_extensions: tuple[str, ...] | None = None,
    allowed_codecs: tuple[str, ...] | None = None,
    max_sample_rate_hz: int | None = None,
    max_bit_depth: int | None = None,
    warn_below_bit_rate_kbps: int | None = None,
) -> AudioCompatibilityProfile:
    if not any(
        value is not None
        for value in (
            allowed_extensions,
            allowed_codecs,
            max_sample_rate_hz,
            max_bit_depth,
            warn_below_bit_rate_kbps,
        )
    ):
        return profile

    return AudioCompatibilityProfile(
        name=f"{profile.name}+custom",
        description=f"Custom overrides based on {profile.name}.",
        allowed_extensions=tuple(_normalize_extension(value) for value in allowed_extensions)
        if allowed_extensions is not None
        else profile.allowed_extensions,
        allowed_codecs=tuple(value.strip().lower() for value in allowed_codecs) if allowed_codecs is not None else profile.allowed_codecs,
        max_sample_rate_hz=max_sample_rate_hz if max_sample_rate_hz is not None else profile.max_sample_rate_hz,
        max_bit_depth=max_bit_depth if max_bit_depth is not None else profile.max_bit_depth,
        warn_below_bit_rate_kbps=warn_below_bit_rate_kbps
        if warn_below_bit_rate_kbps is not None
        else profile.warn_below_bit_rate_kbps,
    )


def _int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _bool_from_text(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "n", "failed", "fail"}


def _normalize_extension(value: str) -> str:
    stripped = value.strip().lower()
    return stripped if stripped.startswith(".") else f".{stripped}"
