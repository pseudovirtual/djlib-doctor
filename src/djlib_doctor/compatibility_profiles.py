from __future__ import annotations

from .compatibility_models import AudioCompatibilityProfile

REKORDBOX_CONSERVATIVE_PROFILE = AudioCompatibilityProfile(
    "rekordbox-conservative",
    "General Rekordbox-oriented USB safety default: AAC/MP3/WAV/AIFF up to 48 kHz and 24-bit PCM.",
    (".aif", ".aiff", ".m4a", ".mp3", ".wav"),
    ("aac", "mp3", "pcm_s16be", "pcm_s16le", "pcm_s24be", "pcm_s24le"),
    48_000,
    24,
)
REKORDBOX_AIFF_16_PROFILE = AudioCompatibilityProfile(
    "rekordbox-aiff-16",
    "AIFF-only workflow with 16-bit PCM.",
    (".aif", ".aiff"),
    ("pcm_s16be", "pcm_s16le"),
    48_000,
    16,
)
REKORDBOX_AIFF_24_PROFILE = AudioCompatibilityProfile(
    "rekordbox-aiff-24",
    "AIFF-only workflow allowing 24-bit PCM up to 48 kHz.",
    (".aif", ".aiff"),
    ("pcm_s16be", "pcm_s16le", "pcm_s24be", "pcm_s24le"),
    48_000,
    24,
)
WAV_16_PROFILE = AudioCompatibilityProfile(
    "wav-16", "WAV-only workflow with 16-bit PCM.", (".wav",), ("pcm_s16le", "pcm_s16be"), 48_000, 16
)
WAV_24_PROFILE = AudioCompatibilityProfile(
    "wav-24",
    "WAV-only workflow allowing 24-bit PCM up to 48 kHz.",
    (".wav",),
    ("pcm_s16le", "pcm_s16be", "pcm_s24le", "pcm_s24be"),
    48_000,
    24,
)
BROAD_SOFTWARE_LIBRARY_PROFILE = AudioCompatibilityProfile(
    "broad-software-library",
    "Broad review profile for AAC/ALAC/FLAC/MP3/WAV/AIFF files.",
    (".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"),
    ("aac", "alac", "flac", "mp3", "pcm_s16be", "pcm_s16le", "pcm_s24be", "pcm_s24le"),
    96_000,
    24,
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


def get_audio_compatibility_profile(name: str) -> AudioCompatibilityProfile:
    try:
        return AUDIO_COMPATIBILITY_PROFILES[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown audio compatibility profile {name!r}. Known profiles: {', '.join(sorted(AUDIO_COMPATIBILITY_PROFILES))}"
        ) from exc


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
        for value in (allowed_extensions, allowed_codecs, max_sample_rate_hz, max_bit_depth, warn_below_bit_rate_kbps)
    ):
        return profile
    return AudioCompatibilityProfile(
        name=f"{profile.name}+custom",
        description=f"Custom overrides based on {profile.name}.",
        allowed_extensions=tuple(_normalize_extension(value) for value in allowed_extensions)
        if allowed_extensions is not None
        else profile.allowed_extensions,
        allowed_codecs=tuple(value.strip().lower() for value in allowed_codecs)
        if allowed_codecs is not None
        else profile.allowed_codecs,
        max_sample_rate_hz=max_sample_rate_hz if max_sample_rate_hz is not None else profile.max_sample_rate_hz,
        max_bit_depth=max_bit_depth if max_bit_depth is not None else profile.max_bit_depth,
        warn_below_bit_rate_kbps=warn_below_bit_rate_kbps
        if warn_below_bit_rate_kbps is not None
        else profile.warn_below_bit_rate_kbps,
    )


def _normalize_extension(value: str) -> str:
    stripped = value.strip().lower()
    return stripped if stripped.startswith(".") else f".{stripped}"
