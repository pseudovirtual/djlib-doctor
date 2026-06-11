from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import csv
import json
from pathlib import Path
from typing import Any

from .compatibility import AudioCompatibilityProfile, AudioProbe, CompatibilitySeverity, check_audio_compatibility
from .collision_policy import DuplicateCollisionPolicy, describe_duplicate_collision_policy, score_duplicate_row
from .compare import compare_exports
from .matching import normalize_text, stem_key
from .path_hygiene import DEFAULT_BAD_PATH_MARKERS, find_bad_path_marker


PLAN_SCHEMA_VERSION = "1.0"


class MatchConfidence(str, Enum):
    EXACT = "exact"
    STRONG = "strong"
    CANDIDATE = "candidate"
    WEAK = "weak"
    UNSAFE = "unsafe"


@dataclass(frozen=True)
class PlanAction:
    action: str
    track_id: str
    artist: str
    title: str
    confidence: MatchConfidence
    human_review_required: bool
    reason: str
    evidence: tuple[str, ...]
    source_path: str = ""
    candidate_path: str = ""
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "track_id": self.track_id,
            "artist": self.artist,
            "title": self.title,
            "confidence": self.confidence.value,
            "human_review_required": self.human_review_required,
            "reason": self.reason,
            "evidence": list(self.evidence),
            "source_path": self.source_path,
            "candidate_path": self.candidate_path,
            "metadata": self.metadata or {},
        }


@dataclass(frozen=True)
class PlanReport:
    plan_type: str
    actions: tuple[PlanAction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PLAN_SCHEMA_VERSION,
            "plan_type": self.plan_type,
            "summary": {
                "actions": len(self.actions),
                "human_review_required": sum(1 for action in self.actions if action.human_review_required),
            },
            "actions": [action.to_dict() for action in self.actions],
        }

    def render_json(self, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(self.to_dict(), indent=2, sort_keys=True)
        return json.dumps(self.to_dict(), sort_keys=True)

    def render_text(self) -> str:
        lines = [
            f"djlib-doctor plan: {self.plan_type}",
            f"Actions: {len(self.actions)}",
            f"Human review required: {sum(1 for action in self.actions if action.human_review_required)}",
        ]
        for action in self.actions:
            candidate = f" -> {action.candidate_path}" if action.candidate_path else ""
            lines.append(f"- {action.action} [{action.confidence.value}] {action.artist} - {action.title}{candidate}")
        return "\n".join(lines)


def build_missing_files_plan(snapshot_path: Path) -> PlanReport:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    artifacts = snapshot.get("artifacts", {})
    missing_path = _artifact_path(snapshot_path, artifacts["missing_files_csv"])
    inventory_path_raw = artifacts.get("filesystem_inventory_csv")
    inventory = _load_inventory(_artifact_path(snapshot_path, inventory_path_raw)) if inventory_path_raw else {}
    rows = _read_csv(missing_path)

    actions = []
    for row in rows:
        source_path = row.get("path", "")
        candidates = inventory.get(stem_key(source_path), [])
        cue_count = _int(row.get("cue_count"))
        playlist_count = _int(row.get("playlist_count"))
        if candidates:
            candidate = candidates[0]
            action = "review_candidate_replacement"
            confidence = MatchConfidence.WEAK
            reason = "A filesystem candidate has the same normalized filename stem; this is not enough for automatic repair."
            evidence = ("same_normalized_filename_stem",)
        elif playlist_count > 0 and cue_count > 0:
            candidate = ""
            action = "reacquire_or_manual_match_preserve_cues"
            confidence = MatchConfidence.UNSAFE
            reason = "Missing cue-bearing record is still used by playlists and has no local candidate."
            evidence = ("playlist_referenced", "cue_bearing", "no_candidate")
        elif playlist_count > 0:
            candidate = ""
            action = "reacquire_or_manual_match"
            confidence = MatchConfidence.UNSAFE
            reason = "Missing record is still used by playlists and has no local candidate."
            evidence = ("playlist_referenced", "no_candidate")
        else:
            candidate = ""
            action = "review_remove_unreferenced_missing_record"
            confidence = MatchConfidence.CANDIDATE
            reason = "Missing record has no playlist references in the snapshot."
            evidence = ("no_playlist_refs",)

        actions.append(
            PlanAction(
                action=action,
                track_id=row.get("track_id", ""),
                artist=row.get("artist", ""),
                title=row.get("title", ""),
                confidence=confidence,
                human_review_required=True,
                reason=reason,
                evidence=evidence,
                source_path=source_path,
                candidate_path=candidate,
            )
        )

    return PlanReport(plan_type="missing-files", actions=tuple(actions))


def build_duplicates_plan(
    snapshot_path: Path,
    collision_policy: DuplicateCollisionPolicy = DuplicateCollisionPolicy.CUE_SAFE,
) -> PlanReport:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    artifacts = snapshot.get("artifacts", {})
    rows = [row for row in _read_csv(_artifact_path(snapshot_path, artifacts["track_summary_csv"])) if row.get("location_kind") != "streaming_placeholder"]
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        sig = (normalize_text(row.get("artist")), normalize_text(row.get("title")))
        if sig[0] and sig[1]:
            groups.setdefault(sig, []).append(row)

    actions = []
    for index, (_, group) in enumerate(sorted(groups.items()), 1):
        if len(group) < 2:
            continue
        survivor = max(group, key=lambda row: score_duplicate_row(row, collision_policy))
        multiple_cued = sum(1 for row in group if _int(row.get("cue_count")) > 0) > 1
        group_id = f"DUP-{index:04d}"
        for row in group:
            is_survivor = row.get("track_id") == survivor.get("track_id")
            if collision_policy is DuplicateCollisionPolicy.KEEP_BOTH:
                action = "keep_duplicate_record"
                confidence = MatchConfidence.CANDIDATE
                reason = "Collision policy says to keep both duplicate records until the DJ makes a manual decision."
            elif is_survivor:
                action = "keep_duplicate_survivor"
                confidence = MatchConfidence.CANDIDATE
                reason = f"Recommended survivor: {describe_duplicate_collision_policy(collision_policy)}"
            elif multiple_cued:
                action = "review_multiple_cued_duplicate"
                confidence = MatchConfidence.UNSAFE
                reason = "Multiple duplicate records have cues; cue union or manual review is required before removing any record."
            elif collision_policy is DuplicateCollisionPolicy.QUALITY and _int(row.get("cue_count")) > 0:
                action = "review_cue_migration_before_removing_duplicate"
                confidence = MatchConfidence.UNSAFE
                reason = "Quality-first policy selected a different survivor; cue migration must be reviewed before removing this record."
            else:
                action = "review_remove_duplicate_later"
                confidence = MatchConfidence.CANDIDATE
                reason = "Duplicate non-survivor can be reviewed after survivor and playlist/cue preservation are verified."
            actions.append(
                PlanAction(
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
                        "group_size": len(group),
                        "recommended_survivor_track_id": survivor.get("track_id", ""),
                        "collision_policy": collision_policy.value,
                        "collision_policy_description": describe_duplicate_collision_policy(collision_policy),
                        "cue_count": _int(row.get("cue_count")),
                        "hotcue_count": _int(row.get("hotcue_count")),
                        "playlist_count": _int(row.get("playlist_count")),
                    },
                )
            )

    return PlanReport(plan_type="duplicates", actions=tuple(actions))


def build_bad_paths_plan(
    snapshot_path: Path,
    markers: tuple[str, ...] = DEFAULT_BAD_PATH_MARKERS,
) -> PlanReport:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    artifacts = snapshot.get("artifacts", {})
    rows = _read_csv(_artifact_path(snapshot_path, artifacts["track_summary_csv"]))

    actions = []
    for row in rows:
        if row.get("location_kind") != "local_file":
            continue
        marker = find_bad_path_marker(row.get("path", ""), markers=markers)
        if not marker:
            continue
        cue_count = _int(row.get("cue_count"))
        playlist_count = _int(row.get("playlist_count"))
        evidence = [f"bad_path_marker:{marker}"]
        if cue_count > 0:
            evidence.append("cue_bearing")
        if playlist_count > 0:
            evidence.append("playlist_referenced")

        if cue_count > 0 or playlist_count > 0:
            action = "review_bad_active_path_before_cleanup"
            confidence = MatchConfidence.UNSAFE
            reason = "Track points at a bad/staging path and still carries cues or playlist references."
        else:
            action = "review_bad_unreferenced_path"
            confidence = MatchConfidence.CANDIDATE
            reason = "Track points at a bad/staging path but has no cues or playlist references in the snapshot."

        actions.append(
            PlanAction(
                action=action,
                track_id=row.get("track_id", ""),
                artist=row.get("artist", ""),
                title=row.get("title", ""),
                confidence=confidence,
                human_review_required=True,
                reason=reason,
                evidence=tuple(evidence),
                source_path=row.get("path", ""),
                metadata={
                    "bad_path_marker": marker,
                    "cue_count": cue_count,
                    "playlist_count": playlist_count,
                },
            )
        )

    return PlanReport(plan_type="bad-paths", actions=tuple(actions))


def build_audio_compatibility_plan(probe_csv_path: Path, profile: AudioCompatibilityProfile | None = None) -> PlanReport:
    rows = _read_csv(probe_csv_path)
    actions = []
    for row in rows:
        probe = AudioProbe.from_dict(row)
        result = check_audio_compatibility(probe, profile=profile) if profile else check_audio_compatibility(probe)
        if not result.issues:
            continue
        has_failure = any(issue.severity is CompatibilitySeverity.FAILURE for issue in result.issues)
        if has_failure:
            action = "review_incompatible_audio_file"
            confidence = MatchConfidence.UNSAFE
            reason = "Audio probe metadata is outside the conservative DJ USB compatibility profile."
        else:
            action = "review_audio_compatibility_warning"
            confidence = MatchConfidence.CANDIDATE
            reason = "Audio probe metadata has warnings that should be reviewed before relying on the file."

        actions.append(
            PlanAction(
                action=action,
                track_id=row.get("track_id", ""),
                artist=row.get("artist", ""),
                title=row.get("title", ""),
                confidence=confidence,
                human_review_required=True,
                reason=reason,
                evidence=tuple(issue.code for issue in result.issues),
                source_path=result.probe.path,
                metadata={
                    "profile": result.profile.name,
                    "issues": [issue.to_dict() for issue in result.issues],
                    "probe": result.to_dict()["probe"],
                },
            )
        )

    return PlanReport(plan_type="audio-compatibility", actions=tuple(actions))


def build_cues_plan(baseline_xml: Path, final_xml: Path) -> PlanReport:
    compare_report = compare_exports(baseline_xml, final_xml)
    actions = []
    for issue in compare_report.issues:
        if issue.code == "cue_not_covered":
            action = "review_add_or_preserve_missing_cue"
            confidence = MatchConfidence.UNSAFE
            evidence = ("baseline_final_compare", "cue_not_covered")
            reason = "A baseline cue time is not covered in the final export. Review before adding or migrating cues."
        elif issue.code == "hotcue_regression":
            action = "review_hotcue_regression"
            confidence = MatchConfidence.UNSAFE
            evidence = ("baseline_final_compare", "hotcue_regression")
            reason = "The final export appears to have fewer hotcues for this material track."
        else:
            continue
        actions.append(
            PlanAction(
                action=action,
                track_id="",
                artist=issue.artist,
                title=issue.title,
                confidence=confidence,
                human_review_required=True,
                reason=reason,
                evidence=evidence,
                metadata={
                    "compare_issue_code": issue.code,
                    "compare_message": issue.message,
                },
            )
        )
    return PlanReport(plan_type="cues", actions=tuple(actions))


def write_plan(report: PlanReport, out_path: Path, pretty: bool = True) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.render_json(pretty=pretty) + "\n", encoding="utf-8")


def load_plan(path: Path) -> PlanReport:
    data = json.loads(path.read_text(encoding="utf-8"))
    actions = []
    for row in data.get("actions", []):
        actions.append(
            PlanAction(
                action=row.get("action", ""),
                track_id=row.get("track_id", ""),
                artist=row.get("artist", ""),
                title=row.get("title", ""),
                confidence=MatchConfidence(row.get("confidence", "unsafe")),
                human_review_required=bool(row.get("human_review_required", True)),
                reason=row.get("reason", ""),
                evidence=tuple(row.get("evidence", [])),
                source_path=row.get("source_path", ""),
                candidate_path=row.get("candidate_path", ""),
                metadata=row.get("metadata", {}),
            )
        )
    return PlanReport(plan_type=data.get("plan_type", "unknown"), actions=tuple(actions))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_inventory(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not path.exists():
        return out
    for row in _read_csv(path):
        out.setdefault(stem_key(row.get("path", "")), []).append(row.get("path", ""))
    return out


def _artifact_path(snapshot_path: Path, artifact_value: str) -> Path:
    path = Path(artifact_value)
    if path.is_absolute():
        return path
    return snapshot_path.parent / path


def _int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _duplicate_evidence(row: dict[str, str], survivor: dict[str, str]) -> tuple[str, ...]:
    evidence = ["same_normalized_artist_title"]
    if row.get("track_id") == survivor.get("track_id"):
        evidence.append("recommended_survivor")
    if _int(row.get("cue_count")) > 0:
        evidence.append("cue_bearing")
    if _int(row.get("playlist_count")) > 0:
        evidence.append("playlist_referenced")
    if row.get("local_exists") == "yes":
        evidence.append("local_file_exists")
    return tuple(evidence)
