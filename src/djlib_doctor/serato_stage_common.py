from __future__ import annotations

from pathlib import Path
from typing import Any

from .stage_common import sha256_file


def manifest_crates(manifest: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(manifest["crates"]) if "crates" in manifest else (manifest,)


def stage_hashes(root: Path, crate_paths: tuple[Path, ...]) -> dict[str, Any]:
    return {"root_sqlite": sha256_file(root), "crates": {str(path): sha256_file(path) for path in crate_paths}}


def install_token_payload(stage_hashes: dict[str, Any], source_hashes: dict[str, str]) -> dict[str, Any]:
    return {"hashes": stage_hashes, "source_hashes": source_hashes}


def file_hash_check(code: str, path: Path, expected_hash: str) -> dict[str, Any]:
    if not path.is_file():
        return {"code": code, "passed": False, "message": f"missing file: {path}"}
    return {"code": code, "passed": sha256_file(path) == expected_hash, "message": str(path)}


def installed_file_record(source: Path, target: Path) -> dict[str, str]:
    return {"source": str(source), "target": str(target), "source_sha256": sha256_file(source), "target_sha256": sha256_file(target)}
