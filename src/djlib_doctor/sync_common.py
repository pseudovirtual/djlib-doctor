from __future__ import annotations

from pathlib import Path
from typing import Any


def required_path(config: dict[str, Any], key: str) -> Path:
    value = str(config.get(key) or "")
    if not value:
        raise ValueError(f"Config {key} is required for sync")
    return Path(value)
