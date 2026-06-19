from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json
from .serato_crate import read_serato_crate


def verify_rekordbox_to_serato_plan(manifest_path: Path, crate_preview_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    expected_tracks = [track["serato_portable_id"] for track in manifest.get("tracks", [])]
    crate = read_serato_crate(crate_preview_path)
    checks = {
        "mode": "passed" if manifest.get("mode") == "dry_run_only" else "failed",
        "target_platform": "passed" if manifest.get("target_platform") == "serato" else "failed",
        "crate_track_order": "passed" if list(crate.tracks) == expected_tracks else "failed",
    }
    return {"passed": all(value == "passed" for value in checks.values()), "checks": checks}
