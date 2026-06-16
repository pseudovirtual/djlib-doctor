from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import sqrt
from pathlib import Path
from typing import Any

from .audio import iter_audio_files


SCHEMA_VERSION = "1.0"
BUCKETS = 16


@dataclass(frozen=True)
class FileFingerprint:
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
class FileComparison:
    left: FileFingerprint
    right: FileFingerprint
    byte_similarity: float
    classification: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "comparison_basis": "raw_file_bytes",
            "claims_audio_identity": False,
            "classification": self.classification,
            "byte_similarity": round(self.byte_similarity, 6),
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


@dataclass(frozen=True)
class FingerprintManifest:
    root: str
    files: tuple[FileFingerprint, ...]
    redacted_paths: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "root": self.root,
            "redacted_paths": self.redacted_paths,
            "file_count": len(self.files),
            "files": [item.to_dict() for item in self.files],
        }


def fingerprint_file(path: Path) -> FileFingerprint:
    data = path.read_bytes()
    return FileFingerprint(
        path=str(path),
        size=len(data),
        sha256=sha256(data).hexdigest(),
        byte_histogram=_byte_histogram(data),
    )


def scan_fingerprints(root: Path, redact_paths: bool = False) -> FingerprintManifest:
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Fingerprint scan root is not a directory: {root}")
    paths = sorted(iter_audio_files(root), key=lambda path: (path.name.lower(), str(path).lower()))
    files = tuple(_with_path(fingerprint_file(path), _scan_path(path, index, redact_paths)) for index, path in enumerate(paths, 1))
    return FingerprintManifest("<redacted>" if redact_paths else str(root), files, redacted_paths=redact_paths)


def compare_files(left: Path, right: Path) -> FileComparison:
    left_fp = fingerprint_file(left)
    right_fp = fingerprint_file(right)
    similarity = 1.0 if left_fp.sha256 == right_fp.sha256 else _cosine(left_fp.byte_histogram, right_fp.byte_histogram)
    return FileComparison(left_fp, right_fp, similarity, _classify(similarity, left_fp.sha256 == right_fp.sha256))


def _with_path(fingerprint: FileFingerprint, path: str) -> FileFingerprint:
    return FileFingerprint(path, fingerprint.size, fingerprint.sha256, fingerprint.byte_histogram)


def _scan_path(path: Path, index: int, redact_paths: bool) -> str:
    return f"<redacted>/track-{index:06d}{path.suffix.lower()}" if redact_paths else str(path)


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
        return "exact_duplicate"
    if similarity >= 0.88:
        return "byte_similar"
    return "different"
