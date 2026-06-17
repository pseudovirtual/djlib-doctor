from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .doctor import build_doctor_report, render_doctor_report


def add_doctor_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("doctor", help="Detect libraries and print a read-only punch list.")
    p.add_argument("--home", type=Path, default=Path.home())
    p.add_argument("--volume", action="append", type=Path)


def handle_doctor(args: argparse.Namespace) -> int:
    try:
        print(render_doctor_report(build_doctor_report(args.home, tuple(args.volume or ()))))
        return 0
    except OSError as exc:
        print(f"djlib-doctor doctor: ERROR\n{exc}", file=sys.stderr)
        return 3
