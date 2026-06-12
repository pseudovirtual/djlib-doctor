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


def install_token(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(raw).hexdigest()[:16]}"


def backup_name(path: Path) -> str:
    safe_parent = "__".join(path.parent.parts[-3:])
    return f"{safe_parent}__{path.name}"
