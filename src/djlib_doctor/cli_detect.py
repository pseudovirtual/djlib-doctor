from __future__ import annotations

import argparse
import json

from .detect import detect_libraries, render_detect_json, render_detect_text


def handle_detect(args: argparse.Namespace) -> int:
    try:
        report = detect_libraries(args.home, tuple(args.volume or ()))
        print(render_detect_json(report, pretty=args.pretty) if args.json else render_detect_text(report))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"detect: {exc}")
        return 1
