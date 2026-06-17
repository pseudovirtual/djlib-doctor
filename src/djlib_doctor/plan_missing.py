from __future__ import annotations

from pathlib import Path

from .io_utils import read_json
from .matching import stem_key
from .plan_io import artifact_path, int_value, load_inventory, read_csv
from .plan_models import MatchConfidence, PlanAction, PlanReport


def build_missing_files_plan(snapshot_path: Path) -> PlanReport:
    snapshot = read_json(snapshot_path)
    artifacts = snapshot.get("artifacts", {})
    rows = read_csv(artifact_path(snapshot_path, artifacts["missing_files_csv"]))
    inventory_path = artifacts.get("filesystem_inventory_csv")
    inventory = load_inventory(artifact_path(snapshot_path, inventory_path)) if inventory_path else {}
    return PlanReport("missing-files", tuple(_missing_action(row, inventory) for row in rows))


def _missing_action(row: dict[str, str], inventory: dict[str, list[str]]) -> PlanAction:
    source_path = row.get("path", "")
    candidates = inventory.get(stem_key(source_path), [])
    cue_count = int_value(row.get("cue_count"))
    playlist_count = int_value(row.get("playlist_count"))
    if candidates:
        action, confidence, reason, evidence, candidate = (
            "review_candidate_replacement",
            MatchConfidence.WEAK,
            "A filesystem candidate has the same normalized filename stem; this is not enough for automatic repair.",
            ("same_normalized_filename_stem",),
            candidates[0],
        )
    elif playlist_count > 0 and cue_count > 0:
        action, confidence, reason, evidence, candidate = (
            "reacquire_or_manual_match_preserve_cues",
            MatchConfidence.UNSAFE,
            "Missing cue-bearing record is still used by playlists and has no local candidate.",
            ("playlist_referenced", "cue_bearing", "no_candidate"),
            "",
        )
    elif playlist_count > 0:
        action, confidence, reason, evidence, candidate = (
            "reacquire_or_manual_match",
            MatchConfidence.UNSAFE,
            "Missing record is still used by playlists and has no local candidate.",
            ("playlist_referenced", "no_candidate"),
            "",
        )
    else:
        action, confidence, reason, evidence, candidate = (
            "review_remove_unreferenced_missing_record",
            MatchConfidence.CANDIDATE,
            "Missing record has no playlist references in the snapshot.",
            ("no_playlist_refs",),
            "",
        )
    return PlanAction(
        action,
        row.get("track_id", ""),
        row.get("artist", ""),
        row.get("title", ""),
        confidence,
        True,
        reason,
        evidence,
        source_path,
        candidate,
    )
