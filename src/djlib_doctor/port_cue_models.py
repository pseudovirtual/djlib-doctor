from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortCueTiming:
    start_ms: int
    end_ms: int | None = None
    slot: int | None = None
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "slot": self.slot,
            "label": self.label,
        }
