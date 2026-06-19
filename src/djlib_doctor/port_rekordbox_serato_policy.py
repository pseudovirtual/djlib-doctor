from __future__ import annotations

from pathlib import Path

SERATO_MANAGED_CRATE_PREFIX = "RB - "
SERATO_FORMAT_CAPABILITIES = {
    ".aif": {
        "status": "supported_for_future_tag_writes",
        "cue_tags": "aiff_id3_geob_markers2",
        "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame.",
    },
    ".aiff": {
        "status": "supported_for_future_tag_writes",
        "cue_tags": "aiff_id3_geob_markers2",
        "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame.",
    },
    ".m4a": {
        "status": "supported_for_future_tag_writes",
        "cue_tags": "mp4_freeform_markersv2",
        "notes": "Serato markersv2 cue data is stored in an MP4 freeform atom.",
    },
    ".mp4": {
        "status": "supported_for_future_tag_writes",
        "cue_tags": "mp4_freeform_markersv2",
        "notes": "Serato markersv2 cue data is stored in an MP4 freeform atom.",
    },
    ".mp3": {
        "status": "supported_for_tag_writes",
        "cue_tags": "id3_geob_markers2",
        "notes": "Serato Markers2 cue data is stored in an ID3 GEOB frame.",
    },
    ".flac": {
        "status": "future_uncertain",
        "cue_tags": "unknown",
        "notes": "Serato FLAC cue metadata needs more fixture-backed validation.",
    },
    ".ogg": {
        "status": "future_uncertain",
        "cue_tags": "unknown",
        "notes": "Serato Ogg cue metadata needs more fixture-backed validation.",
    },
    ".wav": {
        "status": "future_uncertain",
        "cue_tags": "unknown",
        "notes": "Serato WAV cue metadata needs more fixture-backed validation.",
    },
}
CUE_POLICY = {
    "hotcues": "preserve matching Serato hotcue slots 1-8",
    "memory_cues": "promote to first unused Serato hotcue slot",
    "loops": "write saved-loop intent; hotcue loops also keep a hotcue intent",
    "writes_audio_tags": False,
}


def serato_format_capability(path: str) -> dict[str, str]:
    extension = Path(path).suffix.lower()
    default = {
        "status": "unknown",
        "cue_tags": "unknown",
        "notes": "No Serato cue metadata policy is known for this extension.",
    }
    return {"extension": extension.lstrip(".") or "unknown", **SERATO_FORMAT_CAPABILITIES.get(extension, default)}


def format_counts(tracks) -> dict[str, int]:
    counts: dict[str, int] = {}
    for track in tracks:
        extension = serato_format_capability(track.path)["extension"]
        counts[extension] = counts.get(extension, 0) + 1
    return counts


def cue_counts_for_tracks(tracks) -> dict[str, int]:
    return {
        "raw_rekordbox_cue_rows": sum(track.source_cue_count for track in tracks),
        "unique_track_cues": sum(track.source_cue_count for track in tracks),
        "serato_writable_slots": sum(len(track.cue_intents) for track in tracks),
    }


def merge_counts(counts_by_plan) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counts in counts_by_plan:
        for key, value in counts.items():
            merged[key] = merged.get(key, 0) + int(value)
    return merged


def namespace_policy(target_crate_name: str | None = None) -> dict[str, object]:
    crate_name = target_crate_name or ""
    return {
        "managed_prefix": SERATO_MANAGED_CRATE_PREFIX,
        "target_uses_managed_prefix": crate_name.startswith(SERATO_MANAGED_CRATE_PREFIX) if crate_name else True,
        "preserve_existing_unmanaged_crates": True,
        "writes_live_serato_library": False,
        "writes_audio_tags": False,
    }
