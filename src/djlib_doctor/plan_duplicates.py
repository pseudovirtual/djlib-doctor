from __future__ import annotations

from pathlib import Path

from .collision_policy import DuplicateCollisionPolicy, describe_duplicate_collision_policy, score_duplicate_row
from .io_utils import read_json
from .matching import normalize_text
from .plan_io import artifact_path, int_value, read_csv
from .plan_models import MatchConfidence, PlanAction, PlanReport


def build_duplicates_plan(snapshot_path: Path, collision_policy: DuplicateCollisionPolicy = DuplicateCollisionPolicy.CUE_SAFE) -> PlanReport:
    artifacts = read_json(snapshot_path).get("artifacts", {})
    rows = [row for row in read_csv(artifact_path(snapshot_path, artifacts["track_summary_csv"])) if row.get("location_kind") != "streaming_placeholder"]
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        sig = (normalize_text(row.get("artist")), normalize_text(row.get("title")))
        if sig[0] and sig[1]:
            groups.setdefault(sig, []).append(row)
    actions = []
    for index, (_, group) in enumerate(sorted(groups.items()), 1):
        if len(group) > 1:
            actions.extend(_duplicate_actions(f"DUP-{index:04d}", group, collision_policy))
    return PlanReport("duplicates", tuple(actions))


def _duplicate_actions(group_id: str, group: list[dict[str, str]], policy: DuplicateCollisionPolicy) -> list[PlanAction]:
    survivor = max(group, key=lambda row: score_duplicate_row(row, policy))
    multiple_cued = sum(1 for row in group if int_value(row.get("cue_count")) > 0) > 1
    return [_duplicate_action(row, survivor, group_id, len(group), multiple_cued, policy) for row in group]


def _duplicate_action(
    row: dict[str, str],
    survivor: dict[str, str],
    group_id: str,
    group_size: int,
    multiple_cued: bool,
    policy: DuplicateCollisionPolicy,
) -> PlanAction:
    action, confidence, reason = _duplicate_decision(row, survivor, multiple_cued, policy)
    return PlanAction(
        action=action,
        track_id=row.get("track_id", ""),
        artist=row.get("artist", ""),
        title=row.get("title", ""),
        confidence=confidence,
        human_review_required=True,
        reason=reason,
        evidence=_duplicate_evidence(row, survivor),
        source_path=row.get("path", ""),
        metadata={
            "group_id": group_id,
            "group_size": group_size,
            "recommended_survivor_track_id": survivor.get("track_id", ""),
            "collision_policy": policy.value,
            "collision_policy_description": describe_duplicate_collision_policy(policy),
            "cue_count": int_value(row.get("cue_count")),
            "hotcue_count": int_value(row.get("hotcue_count")),
            "playlist_count": int_value(row.get("playlist_count")),
        },
    )


def _duplicate_decision(row: dict[str, str], survivor: dict[str, str], multiple_cued: bool, policy: DuplicateCollisionPolicy):
    if policy is DuplicateCollisionPolicy.KEEP_BOTH:
        return "keep_duplicate_record", MatchConfidence.CANDIDATE, "Collision policy says to keep both duplicate records until the DJ makes a manual decision."
    if row.get("track_id") == survivor.get("track_id"):
        return "keep_duplicate_survivor", MatchConfidence.CANDIDATE, f"Recommended survivor: {describe_duplicate_collision_policy(policy)}"
    if multiple_cued:
        return "review_multiple_cued_duplicate", MatchConfidence.UNSAFE, "Multiple duplicate records have cues; cue union or manual review is required before removing any record."
    if policy is DuplicateCollisionPolicy.QUALITY and int_value(row.get("cue_count")) > 0:
        return "review_cue_migration_before_removing_duplicate", MatchConfidence.UNSAFE, "Quality-first policy selected a different survivor; cue migration must be reviewed before removing this record."
    return "review_remove_duplicate_later", MatchConfidence.CANDIDATE, "Duplicate non-survivor can be reviewed after survivor and playlist/cue preservation are verified."


def _duplicate_evidence(row: dict[str, str], survivor: dict[str, str]) -> tuple[str, ...]:
    evidence = ["same_normalized_artist_title"]
    if row.get("track_id") == survivor.get("track_id"):
        evidence.append("recommended_survivor")
    if int_value(row.get("cue_count")) > 0:
        evidence.append("cue_bearing")
    if int_value(row.get("playlist_count")) > 0:
        evidence.append("playlist_referenced")
    if row.get("local_exists") == "yes":
        evidence.append("local_file_exists")
    return tuple(evidence)
