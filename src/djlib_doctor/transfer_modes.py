from __future__ import annotations

TRANSFER_MODES = ("full", "cues-only", "match-only")


def validate_transfer_mode(value: str) -> None:
    if value not in TRANSFER_MODES:
        raise ValueError(f"Unsupported transfer mode: {value}")
