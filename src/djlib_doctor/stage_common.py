from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(path: Path, expected_hash: str, description: str) -> None:
    if sha256_file(path) != expected_hash:
        raise RuntimeError(f"{description} hash mismatch: {path}")


def install_token(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(raw).hexdigest()[:16]}"


def require_install_token(prefix: str, payload: object, recorded_token: str, confirm_token: str) -> None:
    if confirm_token != recorded_token:
        raise ValueError("Confirmation token does not match staged install token")
    if install_token(prefix, payload) != recorded_token:
        raise RuntimeError("Stage manifest install token does not match manifest contents")


def backup_name(path: Path) -> str:
    safe_parent = "__".join(path.parent.parts[-3:])
    return f"{safe_parent}__{path.name}"
