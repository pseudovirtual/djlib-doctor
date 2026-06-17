from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, TextIO

from .plan import PlanAction, PlanReport
from .reviewer_choices import ReviewChoice, choices_for_action
from .reviewer_log import REVIEW_SCHEMA_VERSION, ReviewDecision, ReviewLog, load_review_log, write_review_log

__all__ = [
    "REVIEW_SCHEMA_VERSION",
    "ReviewDecision",
    "ReviewLog",
    "load_review_log",
    "run_interactive_review",
    "write_review_log",
]


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

    index = 0
    while index < total:
        action = report.actions[index]
        review_id = f"{report.plan_type.upper()}-{index + 1:04d}"
        choices = choices_for_action(report.plan_type, action)
        print("", file=output)
        print(f"Progress: {len(decisions)}/{total} reviewed, {total - len(decisions)} remaining", file=output)
        _print_action(review_id, index + 1, total, action, choices, output)
        selected = _prompt_choice(choices, input_func, output)
        if selected == "quit":
            break
        if selected == "undo":
            if decisions:
                undone = decisions.pop()
                index = max(0, index - 1)
                write_review_log(report, tuple(decisions), out_path)
                print(f"Undid: {undone.review_id}", file=output)
            else:
                print("Nothing to undo.", file=output)
            continue
        if selected == "accept_remaining":
            accepted = _accept_remaining(report, index, decisions)
            index += accepted
            write_review_log(report, tuple(decisions), out_path)
            print(f"Accepted recommended for {accepted} remaining high-confidence rows.", file=output)
            continue
        notes = "" if selected == "skip" else input_func("Notes (optional): ").strip()
        decisions.append(ReviewDecision(review_id=review_id, action=action, decision=selected, notes=notes))
        write_review_log(report, tuple(decisions), out_path)
        print(f"Recorded: {selected}", file=output)
        index += 1

    write_review_log(report, tuple(decisions), out_path)
    print("", file=output)
    print(f"Review decisions written: {out_path}", file=output)
    return tuple(decisions)


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
    detail_rows = (
        ("Why", action.reason),
        ("Evidence", ", ".join(action.evidence)),
        ("Source", action.source_path),
        ("Candidate", action.candidate_path),
        ("Context", _metadata_summary(action)),
    )
    for label, value in detail_rows:
        if value:
            print(f"{label}: {value}", file=output)
    print("Choices:", file=output)
    for number, choice in enumerate(choices, 1):
        print(f"  {number}. {choice.label} ({choice.value})", file=output)
    print(f"  Enter. Accept recommended ({_recommended_choice(choices)})", file=output)
    print("  A. Accept recommended for remaining high-confidence rows", file=output)
    print("  u. Undo last decision", file=output)
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
        if raw in {"u", "a"}:
            return {"u": "undo", "a": "accept_remaining"}[raw]
        if raw == "":
            return _recommended_choice(choices)
        if raw == "s":
            return "skip"
        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < len(choices):
                return choices[index].value
        for choice in choices:
            if raw == choice.value:
                return choice.value
        print("Choose a number, decision value, Enter, A, u, s, or q.", file=output)


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


def _recommended_choice(choices: tuple[ReviewChoice, ...]) -> str:
    return choices[0].value if choices else "skip"


def _is_high_confidence(action: PlanAction) -> bool:
    return action.confidence.value in {"exact", "strong"}


def _accept_remaining(report: PlanReport, index: int, decisions: list[ReviewDecision]) -> int:
    accepted = 0
    while index + accepted < len(report.actions) and _is_high_confidence(report.actions[index + accepted]):
        action = report.actions[index + accepted]
        decisions.append(
            ReviewDecision(
                review_id=f"{report.plan_type.upper()}-{index + accepted + 1:04d}",
                action=action,
                decision=_recommended_choice(choices_for_action(report.plan_type, action)),
            )
        )
        accepted += 1
    return accepted
