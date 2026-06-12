from __future__ import annotations

from pathlib import Path

from .compatibility import AudioCompatibilityProfile, AudioProbe, CompatibilitySeverity, check_audio_compatibility
from .compare import compare_exports
from .io_utils import read_json
from .path_hygiene import DEFAULT_BAD_PATH_MARKERS, find_bad_path_marker
from .plan_io import artifact_path, int_value, read_csv
from .plan_models import MatchConfidence, PlanAction, PlanReport


def build_bad_paths_plan(snapshot_path: Path, markers: tuple[str, ...] = DEFAULT_BAD_PATH_MARKERS) -> PlanReport:
    artifacts = read_json(snapshot_path).get("artifacts", {})
    rows = read_csv(artifact_path(snapshot_path, artifacts["track_summary_csv"]))
    actions = [_bad_path_action(row, find_bad_path_marker(row.get("path", ""), markers=markers)) for row in rows if row.get("location_kind") == "local_file"]
    return PlanReport("bad-paths", tuple(action for action in actions if action))


def _bad_path_action(row: dict[str, str], marker: str | None) -> PlanAction | None:
    if not marker:
        return None
    cue_count = int_value(row.get("cue_count"))
    playlist_count = int_value(row.get("playlist_count"))
    risky = cue_count > 0 or playlist_count > 0
    evidence = [f"bad_path_marker:{marker}"]
    evidence.extend(label for label, present in (("cue_bearing", cue_count > 0), ("playlist_referenced", playlist_count > 0)) if present)
    return PlanAction(
        action="review_bad_active_path_before_cleanup" if risky else "review_bad_unreferenced_path",
        track_id=row.get("track_id", ""),
        artist=row.get("artist", ""),
        title=row.get("title", ""),
        confidence=MatchConfidence.UNSAFE if risky else MatchConfidence.CANDIDATE,
        human_review_required=True,
        reason="Track points at a bad/staging path and still carries cues or playlist references." if risky else "Track points at a bad/staging path but has no cues or playlist references in the snapshot.",
        evidence=tuple(evidence),
        source_path=row.get("path", ""),
        metadata={"bad_path_marker": marker, "cue_count": cue_count, "playlist_count": playlist_count},
    )


def build_audio_compatibility_plan(probe_csv_path: Path, profile: AudioCompatibilityProfile | None = None) -> PlanReport:
    actions = []
    for row in read_csv(probe_csv_path):
        probe = AudioProbe.from_dict(row)
        result = check_audio_compatibility(probe, profile=profile) if profile else check_audio_compatibility(probe)
        if result.issues:
            has_failure = any(issue.severity is CompatibilitySeverity.FAILURE for issue in result.issues)
            actions.append(
                PlanAction(
                    action="review_incompatible_audio_file" if has_failure else "review_audio_compatibility_warning",
                    track_id=row.get("track_id", ""),
                    artist=row.get("artist", ""),
                    title=row.get("title", ""),
                    confidence=MatchConfidence.UNSAFE if has_failure else MatchConfidence.CANDIDATE,
                    human_review_required=True,
                    reason="Audio probe metadata is outside the conservative DJ USB compatibility profile." if has_failure else "Audio probe metadata has warnings that should be reviewed before relying on the file.",
                    evidence=tuple(issue.code for issue in result.issues),
                    source_path=result.probe.path,
                    metadata={"profile": result.profile.name, "issues": [issue.to_dict() for issue in result.issues], "probe": result.to_dict()["probe"]},
                )
            )
    return PlanReport("audio-compatibility", tuple(actions))


def build_cues_plan(baseline_xml: Path, final_xml: Path) -> PlanReport:
    actions = []
    for issue in compare_exports(baseline_xml, final_xml).issues:
        if issue.code not in {"cue_not_covered", "hotcue_regression"}:
            continue
        actions.append(
            PlanAction(
                action="review_add_or_preserve_missing_cue" if issue.code == "cue_not_covered" else "review_hotcue_regression",
                track_id="",
                artist=issue.artist,
                title=issue.title,
                confidence=MatchConfidence.UNSAFE,
                human_review_required=True,
                reason="A baseline cue time is not covered in the final export. Review before adding or migrating cues." if issue.code == "cue_not_covered" else "The final export appears to have fewer hotcues for this material track.",
                evidence=("baseline_final_compare", issue.code),
                metadata={"compare_issue_code": issue.code, "compare_message": issue.message},
            )
        )
    return PlanReport("cues", tuple(actions))
