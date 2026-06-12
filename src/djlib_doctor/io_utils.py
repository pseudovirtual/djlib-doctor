from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_json(data: Any, pretty: bool = False) -> str:
    return json.dumps(data, indent=2, sort_keys=True) if pretty else json.dumps(data, sort_keys=True)


def write_json(path: Path, data: Any, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(data, pretty=pretty) + "\n", encoding="utf-8")
