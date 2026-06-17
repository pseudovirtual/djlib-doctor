from __future__ import annotations

import argparse
import json
from pathlib import Path

from .detect import detect_libraries, render_detect_json, render_detect_text


def add_detect_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("detect", help="Read-only probe for Rekordbox and Serato library paths.")
    p.add_argument("--home", type=Path, default=Path.home())
    p.add_argument("--volume", action="append", type=Path)
    p.add_argument("--json", action="store_true")
    p.add_argument("--pretty", action="store_true")


def handle_detect(args: argparse.Namespace) -> int:
    try:
        report = detect_libraries(args.home, tuple(args.volume or ()))
        print(render_detect_json(report, pretty=args.pretty) if args.json else render_detect_text(report))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"detect: {exc}")
        return 1
