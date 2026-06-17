from __future__ import annotations

import argparse
from pathlib import Path

from .cli_common import fail
from .doctor import build_doctor_report, render_doctor_report


def add_doctor_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("doctor", help="Detect libraries and print a read-only punch list.")
    p.add_argument("--home", type=Path, default=Path.home())
    p.add_argument("--volume", action="append", type=Path)
    p.add_argument("--config", type=Path)


def handle_doctor(args: argparse.Namespace) -> int:
    try:
        print(render_doctor_report(build_doctor_report(args.home, tuple(args.volume or ()), args.config)))
        return 0
    except OSError as exc:
        return fail("doctor", exc)
