from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Callable, TextIO

from .plan import PlanAction, PlanReport


REVIEW_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ReviewChoice:
    value: str
    label: str


@dataclass(frozen=True)
class ReviewDecision:
    review_id: str
    action: PlanAction
    decision: str
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "decision": self.decision,
            "notes": self.notes,
            "action": self.action.to_dict(),
        }


@dataclass(frozen=True)
class ReviewLog:
    source_plan_type: str
    decisions: tuple[ReviewDecision, ...]

    def by_review_id(self) -> dict[str, ReviewDecision]:
        return {decision.review_id: decision for decision in self.decisions}


def run_interactive_review(
    report: PlanReport,
    out_path: Path,
    input_func: Callable[[str], str] = input,
    output: TextIO | None = None,
) -> tuple[ReviewDecision, ...]:
    output = output if output is not None else sys.stdout
    decisions: list[ReviewDecision] = []
    total = len(report.actions)

    print(f"djlib-doctor review: {report.plan_type}", file=output)
    print(f"Rows: {total}", file=output)
    print("No changes will be applied. Decisions are recorded only.", file=output)

    for index, action in enumerate(report.actions, 1):
        review_id = f"{report.plan_type.upper()}-{index:04d}"
        choices = choices_for_action(report.plan_type, action)
        print("", file=output)
        _print_action(review_id, index, total, action, choices, output)
        selected = _prompt_choice(choices, input_func, output)
        if selected == "quit":
            break
        if selected == "skip":
            notes = ""
        else:
            notes = input_func("Notes (optional): ").strip()
        decisions.append(ReviewDecision(review_id=review_id, action=action, decision=selected, notes=notes))
        write_review_log(report, tuple(decisions), out_path)
        print(f"Recorded: {selected}", file=output)

    write_review_log(report, tuple(decisions), out_path)
    print("", file=output)
    print(f"Review decisions written: {out_path}", file=output)
    return tuple(decisions)


def load_review_log(path: Path) -> ReviewLog:
    data = json.loads(path.read_text(encoding="utf-8"))
    decisions = []
    for row in data.get("decisions", []):
        action_data = row.get("action", {})
        decisions.append(
            ReviewDecision(
                review_id=row.get("review_id", ""),
                action=_action_from_dict(action_data),
                decision=row.get("decision", ""),
                notes=row.get("notes", ""),
            )
        )
    return ReviewLog(source_plan_type=data.get("source_plan_type", ""), decisions=tuple(decisions))


def write_review_log(report: PlanReport, decisions: tuple[ReviewDecision, ...], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "source_plan_type": report.plan_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "plan_actions": len(report.actions),
            "decisions": len(decisions),
            "unreviewed": len(report.actions) - len(decisions),
        },
        "decisions": [decision.to_dict() for decision in decisions],
    }
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def choices_for_action(plan_type: str, action: PlanAction) -> tuple[ReviewChoice, ...]:
    if plan_type == "missing-files":
        return (
            ReviewChoice("reacquire", "Reacquire the track later"),
            ReviewChoice("manual_match", "Manually find or relink a replacement"),
            ReviewChoice("remove_dead_record_later", "Approve reviewing/removing the dead record later"),
            ReviewChoice("keep_for_now", "Keep the record for now"),
            ReviewChoice("needs_listening", "Needs listening or manual investigation"),
        )
    if plan_type == "duplicates":
        return (
            ReviewChoice("keep_recommended", "Keep the recommended record"),
            ReviewChoice("keep_both", "Keep both duplicate records"),
            ReviewChoice("prefer_quality", "Prefer the higher-quality file"),
            ReviewChoice("prefer_cues", "Prefer the better cue-bearing record"),
            ReviewChoice("needs_listening", "Needs listening or cue review"),
        )
    if plan_type == "bad-paths":
        return (
            ReviewChoice("find_clean_keeper", "Find or create a clean keeper path later"),
            ReviewChoice("keep_for_now", "Keep this path for now"),
            ReviewChoice("remove_or_relink_later", "Review removal or relink later"),
            ReviewChoice("needs_investigation", "Needs manual investigation"),
        )
    if plan_type == "audio-compatibility":
        return (
            ReviewChoice("accept_for_target", "Accept this file for the target setup"),
            ReviewChoice("convert_later", "Convert or replace later"),
            ReviewChoice("exclude_from_usb", "Exclude from USB/export target"),
            ReviewChoice("needs_probe_review", "Needs probe/listening review"),
        )
    if plan_type == "cues":
        return (
            ReviewChoice("preserve_or_add_cue_later", "Preserve or add this cue later"),
            ReviewChoice("accept_difference", "Accept the cue difference"),
            ReviewChoice("needs_listening", "Needs listening/cue review"),
        )
    return (
        ReviewChoice("approve", "Approve this recommendation for future planning"),
        ReviewChoice("skip", "Skip this row"),
        ReviewChoice("needs_review", "Needs review"),
    )


def _print_action(
    review_id: str,
    index: int,
    total: int,
    action: PlanAction,
    choices: tuple[ReviewChoice, ...],
    output: TextIO,
) -> None:
    print(f"[{index}/{total}] {review_id}", file=output)
    print(f"{action.artist or '(unknown artist)'} - {action.title or '(unknown title)'}", file=output)
    print(f"Action: {action.action} [{action.confidence.value}]", file=output)
    if action.reason:
        print(f"Why: {action.reason}", file=output)
    if action.evidence:
        print(f"Evidence: {', '.join(action.evidence)}", file=output)
    if action.source_path:
        print(f"Source: {action.source_path}", file=output)
    if action.candidate_path:
        print(f"Candidate: {action.candidate_path}", file=output)
    metadata_summary = _metadata_summary(action)
    if metadata_summary:
        print(f"Context: {metadata_summary}", file=output)
    print("Choices:", file=output)
    for number, choice in enumerate(choices, 1):
        print(f"  {number}. {choice.label} ({choice.value})", file=output)
    print("  s. Skip this row", file=output)
    print("  q. Save and quit", file=output)


def _prompt_choice(
    choices: tuple[ReviewChoice, ...],
    input_func: Callable[[str], str],
    output: TextIO,
) -> str:
    while True:
        raw = input_func("Decision: ").strip().lower()
        if raw == "q":
            return "quit"
        if raw in {"s", ""}:
            return "skip"
        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < len(choices):
                return choices[index].value
        for choice in choices:
            if raw == choice.value:
                return choice.value
        print("Choose a number, decision value, s to skip, or q to quit.", file=output)


def _metadata_summary(action: PlanAction) -> str:
    metadata = action.metadata or {}
    interesting = (
        "group_id",
        "group_size",
        "recommended_survivor_track_id",
        "collision_policy",
        "cue_count",
        "hotcue_count",
        "playlist_count",
        "bad_path_marker",
        "profile",
    )
    parts = [f"{key}={metadata[key]}" for key in interesting if key in metadata]
    return ", ".join(parts)


def _action_from_dict(data: dict[str, object]) -> PlanAction:
    from .plan import MatchConfidence

    return PlanAction(
        action=str(data.get("action", "")),
        track_id=str(data.get("track_id", "")),
        artist=str(data.get("artist", "")),
        title=str(data.get("title", "")),
        confidence=MatchConfidence(str(data.get("confidence", "unsafe"))),
        human_review_required=bool(data.get("human_review_required", True)),
        reason=str(data.get("reason", "")),
        evidence=tuple(str(item) for item in data.get("evidence", [])),
        source_path=str(data.get("source_path", "")),
        candidate_path=str(data.get("candidate_path", "")),
        metadata=data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
    )
