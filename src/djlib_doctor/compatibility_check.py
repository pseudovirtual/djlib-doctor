from __future__ import annotations

from .compatibility_models import AudioCompatibilityProfile, AudioProbe, CompatibilityIssue, CompatibilityResult, CompatibilitySeverity
from .compatibility_profiles import REKORDBOX_CONSERVATIVE_PROFILE


def check_audio_compatibility(probe: AudioProbe, profile: AudioCompatibilityProfile = REKORDBOX_CONSERVATIVE_PROFILE) -> CompatibilityResult:
    issues: list[CompatibilityIssue] = []
    if not probe.probe_ok:
        issues.append(_issue("probe_failed", CompatibilitySeverity.FAILURE, "Audio probe did not complete; compatibility cannot be trusted."))
    if probe.extension.lower() and probe.extension.lower() not in profile.allowed_extensions:
        issues.append(_issue("unsupported_extension", CompatibilitySeverity.FAILURE, f"Extension {probe.extension.lower()} is outside the {profile.name} profile."))
    if not probe.codec:
        issues.append(_issue("unknown_codec", CompatibilitySeverity.WARNING, "Codec is missing from probe metadata."))
    elif probe.codec.lower() not in profile.allowed_codecs:
        issues.append(_issue("unsupported_codec", CompatibilitySeverity.FAILURE, f"Codec {probe.codec.lower()} is outside the {profile.name} profile."))
    if probe.sample_rate_hz is not None and probe.sample_rate_hz > profile.max_sample_rate_hz:
        issues.append(_issue("sample_rate_too_high", CompatibilitySeverity.FAILURE, f"Sample rate {probe.sample_rate_hz} Hz exceeds {profile.max_sample_rate_hz} Hz."))
    if probe.bit_depth is not None and probe.bit_depth > profile.max_bit_depth:
        issues.append(_issue("bit_depth_too_high", CompatibilitySeverity.FAILURE, f"Bit depth {probe.bit_depth} exceeds {profile.max_bit_depth}."))
    if probe.duration_seconds is not None and probe.duration_seconds <= 0:
        issues.append(_issue("invalid_duration", CompatibilitySeverity.WARNING, "Duration is zero or negative."))
    if probe.bit_rate_kbps is not None and 0 < probe.bit_rate_kbps < profile.warn_below_bit_rate_kbps:
        issues.append(_issue("low_bit_rate", CompatibilitySeverity.WARNING, f"Bit rate {probe.bit_rate_kbps} kbps is below {profile.warn_below_bit_rate_kbps} kbps."))
    return CompatibilityResult(probe, profile, tuple(issues))


def _issue(code: str, severity: CompatibilitySeverity, message: str) -> CompatibilityIssue:
    return CompatibilityIssue(code, severity, message)
