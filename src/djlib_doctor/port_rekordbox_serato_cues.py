from __future__ import annotations

from .cues import CueType
from .port_rekordbox_serato_models import SeratoCueIntent
from .rekordbox_xml import Cue


def cue_intents(cues: tuple[Cue, ...]) -> tuple[tuple[SeratoCueIntent, ...], tuple[str, ...]]:
    intents = []
    unsupported = []
    used_hotcue_slots: set[int] = set()
    used_loop_slots: set[int] = set()
    for cue in sorted(cues, key=lambda item: (item.slot if item.slot is not None else 99, item.start)):
        if cue.kind.value == "hotcue" and cue.slot is not None:
            if 0 <= cue.slot <= 7:
                used_hotcue_slots.add(cue.slot)
                intents.append(_hotcue_intent(cue, cue.slot))
            else:
                unsupported.append(f"hotcue_slot_out_of_serato_range:{cue.slot}")
        elif cue.cue_type is not CueType.LOOP:
            _append_memory_cue(cue, intents, unsupported, used_hotcue_slots)
        if cue.cue_type is CueType.LOOP:
            _append_loop(cue, intents, unsupported, used_loop_slots)
    return tuple(intents), tuple(unsupported)


def _append_memory_cue(cue: Cue, intents: list[SeratoCueIntent], unsupported: list[str], used: set[int]) -> None:
    slot = _next_unused_slot(used)
    if slot is None:
        unsupported.append("no_serato_hotcue_slot_for_memory_cue")
    else:
        used.add(slot)
        intents.append(_hotcue_intent(cue, slot, label=_cue_label(cue) or f"Memory {slot + 1}"))


def _append_loop(cue: Cue, intents: list[SeratoCueIntent], unsupported: list[str], used: set[int]) -> None:
    slot = cue.slot if cue.slot is not None and 0 <= cue.slot <= 7 else _next_unused_slot(used)
    if slot is None:
        unsupported.append("no_serato_loop_slot")
    else:
        used.add(slot)
        intents.append(
            SeratoCueIntent(
                "serato_saved_loop",
                _cue_ms(cue.start),
                None if cue.end is None else _cue_ms(cue.end),
                slot,
                _cue_label(cue) or f"Loop {slot + 1}",
                cue.kind.value,
                cue.cue_type.value,
            )
        )


def _hotcue_intent(cue: Cue, slot: int, label: str = "") -> SeratoCueIntent:
    return SeratoCueIntent(
        "serato_hotcue",
        _cue_ms(cue.start),
        None,
        slot,
        label or _cue_label(cue) or chr(ord("A") + slot),
        cue.kind.value,
        cue.cue_type.value,
    )


def _cue_ms(value: float) -> int:
    return int(round(value * 1000))


def _cue_label(cue: Cue) -> str:
    return cue.name or cue.hotcue_label or ""


def _next_unused_slot(used: set[int]) -> int | None:
    return next((index for index in range(8) if index not in used), None)
