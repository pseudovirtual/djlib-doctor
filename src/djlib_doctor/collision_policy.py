from __future__ import annotations

from enum import Enum


class DuplicateCollisionPolicy(str, Enum):
    CUE_SAFE = "cue-safe"
    QUALITY = "quality"
    KEEP_BOTH = "keep-both"


def get_duplicate_collision_policy(value: str) -> DuplicateCollisionPolicy:
    try:
        return DuplicateCollisionPolicy(value)
    except ValueError as exc:
        known = ", ".join(policy.value for policy in DuplicateCollisionPolicy)
        raise ValueError(f"Unknown duplicate collision policy {value!r}. Known policies: {known}") from exc


def score_duplicate_row(row: dict[str, str], policy: DuplicateCollisionPolicy) -> int:
    if policy is DuplicateCollisionPolicy.KEEP_BOTH:
        return 0
    if policy is DuplicateCollisionPolicy.QUALITY:
        return _quality_first_score(row)
    return _cue_safe_score(row)


def describe_duplicate_collision_policy(policy: DuplicateCollisionPolicy) -> str:
    if policy is DuplicateCollisionPolicy.QUALITY:
        return "Prefer the most compatible/high-quality local file, while marking cue migration risks for human review."
    if policy is DuplicateCollisionPolicy.KEEP_BOTH:
        return "Keep duplicate records as intentional until the DJ decides otherwise."
    return "Prefer cue-bearing and playlist-referenced records before considering file quality."


def _cue_safe_score(row: dict[str, str]) -> int:
    score = 0
    score += _int(row.get("cue_count")) * 10_000
    score += _int(row.get("hotcue_count")) * 2_000
    score += _int(row.get("playlist_count")) * 500
    if row.get("local_exists") == "yes":
        score += 1_000
    score += _format_quality_score(row)
    score += _path_penalty(row)
    return score


def _quality_first_score(row: dict[str, str]) -> int:
    score = 0
    if row.get("local_exists") == "yes":
        score += 5_000
    score += _format_quality_score(row) * 8
    score += _int(row.get("playlist_count")) * 500
    score += _int(row.get("cue_count")) * 1_000
    score += _int(row.get("hotcue_count")) * 250
    score += _path_penalty(row)
    return score


def _format_quality_score(row: dict[str, str]) -> int:
    kind = (row.get("kind") or "").lower()
    path = (row.get("path") or "").lower()
    text = f"{kind} {path}"
    if "aiff" in text or ".aif" in text or "wav" in text or ".wav" in text:
        return 300
    if "flac" in text or ".flac" in text:
        return 250
    if "m4a" in text or ".m4a" in text:
        return 200
    if "mp3" in text or ".mp3" in text:
        return 100
    return 0


def _path_penalty(row: dict[str, str]) -> int:
    path = row.get("path", "").lower()
    if "_old" in path or "superseded" in path or "backup" in path:
        return -5_000
    return 0


def _int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0
