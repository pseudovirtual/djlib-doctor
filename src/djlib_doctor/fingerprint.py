from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import sqrt
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
BUCKETS = 16


@dataclass(frozen=True)
class TrackFingerprint:
    path: str
    size: int
    sha256: str
    byte_histogram: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "size": self.size,
            "sha256": self.sha256,
            "byte_histogram": list(self.byte_histogram),
        }


@dataclass(frozen=True)
class TrackComparison:
    left: TrackFingerprint
    right: TrackFingerprint
    similarity: float
    classification: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "classification": self.classification,
            "similarity": round(self.similarity, 6),
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


def fingerprint_file(path: Path) -> TrackFingerprint:
    data = path.read_bytes()
    return TrackFingerprint(
        path=str(path),
        size=len(data),
        sha256=sha256(data).hexdigest(),
        byte_histogram=_byte_histogram(data),
    )


def compare_tracks(left: Path, right: Path) -> TrackComparison:
    left_fp = fingerprint_file(left)
    right_fp = fingerprint_file(right)
    similarity = 1.0 if left_fp.sha256 == right_fp.sha256 else _cosine(left_fp.byte_histogram, right_fp.byte_histogram)
    return TrackComparison(left_fp, right_fp, similarity, _classify(similarity, left_fp.sha256 == right_fp.sha256))


def _byte_histogram(data: bytes) -> tuple[float, ...]:
    if not data:
        return (0.0,) * BUCKETS
    counts = [0] * BUCKETS
    for byte in data:
        counts[byte * BUCKETS // 256] += 1
    return tuple(count / len(data) for count in counts)


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _classify(similarity: float, exact: bool) -> str:
    if exact:
        return "same"
    if similarity >= 0.88:
        return "similar"
    return "different"
