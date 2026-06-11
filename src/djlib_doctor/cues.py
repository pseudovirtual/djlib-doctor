from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CueKind(str, Enum):
    MEMORY = "memory"
    HOTCUE = "hotcue"


class CueType(str, Enum):
    CUE = "cue"
    LOOP = "loop"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Cue:
    kind: CueKind
    cue_type: CueType
    start: float
    end: Optional[float] = None
    slot: Optional[int] = None
    name: Optional[str] = None
    color: Optional[str] = None

    @property
    def hotcue_label(self) -> Optional[str]:
        if self.kind is not CueKind.HOTCUE or self.slot is None:
            return None
        if 0 <= self.slot <= 25:
            return chr(ord("A") + self.slot)
        return str(self.slot)


def parse_cue_num(raw_num: Optional[str]) -> tuple[CueKind, Optional[int]]:
    if raw_num is None:
        return CueKind.MEMORY, None

    try:
        num = int(raw_num)
    except ValueError:
        return CueKind.MEMORY, None

    if num < 0:
        return CueKind.MEMORY, None
    return CueKind.HOTCUE, num


def parse_cue_type(raw_type: Optional[str]) -> CueType:
    if raw_type == "0":
        return CueType.CUE
    if raw_type == "4":
        return CueType.LOOP
    return CueType.UNKNOWN


def parse_position(raw_position: Optional[str]) -> float:
    if raw_position in (None, ""):
        return 0.0
    return float(raw_position)
