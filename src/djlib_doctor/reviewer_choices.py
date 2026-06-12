from __future__ import annotations

from dataclasses import dataclass

from .plan import PlanAction


@dataclass(frozen=True)
class ReviewChoice:
    value: str
    label: str


CHOICES = {
    "missing-files": (
        ReviewChoice("reacquire", "Reacquire the track later"),
        ReviewChoice("manual_match", "Manually find or relink a replacement"),
        ReviewChoice("remove_dead_record_later", "Approve reviewing/removing the dead record later"),
        ReviewChoice("keep_for_now", "Keep the record for now"),
        ReviewChoice("needs_listening", "Needs listening or manual investigation"),
    ),
    "duplicates": (
        ReviewChoice("keep_recommended", "Keep the recommended record"),
        ReviewChoice("keep_both", "Keep both duplicate records"),
        ReviewChoice("prefer_quality", "Prefer the higher-quality file"),
        ReviewChoice("prefer_cues", "Prefer the better cue-bearing record"),
        ReviewChoice("needs_listening", "Needs listening or cue review"),
    ),
    "bad-paths": (
        ReviewChoice("find_clean_keeper", "Find or create a clean keeper path later"),
        ReviewChoice("keep_for_now", "Keep this path for now"),
        ReviewChoice("remove_or_relink_later", "Review removal or relink later"),
        ReviewChoice("needs_investigation", "Needs manual investigation"),
    ),
    "audio-compatibility": (
        ReviewChoice("accept_for_target", "Accept this file for the target setup"),
        ReviewChoice("convert_later", "Convert or replace later"),
        ReviewChoice("exclude_from_usb", "Exclude from USB/export target"),
        ReviewChoice("needs_probe_review", "Needs probe/listening review"),
    ),
    "cues": (
        ReviewChoice("preserve_or_add_cue_later", "Preserve or add this cue later"),
        ReviewChoice("accept_difference", "Accept the cue difference"),
        ReviewChoice("needs_listening", "Needs listening/cue review"),
    ),
}
DEFAULT_CHOICES = (
    ReviewChoice("approve", "Approve this recommendation for future planning"),
    ReviewChoice("skip", "Skip this row"),
    ReviewChoice("needs_review", "Needs review"),
)


def choices_for_action(plan_type: str, action: PlanAction) -> tuple[ReviewChoice, ...]:
    return CHOICES.get(plan_type, DEFAULT_CHOICES)
