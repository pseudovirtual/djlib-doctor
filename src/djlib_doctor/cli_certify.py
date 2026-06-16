from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .certify import certify_port_manifest, write_certification_report
from .io_utils import render_json


def add_certify_parser(sub: argparse._SubParsersAction) -> None:
    cert = sub.add_parser("certify", help="Certify dry-run migration artifacts.").add_subparsers(
        dest="certify_command", required=True
    )
    port = cert.add_parser("port")
    port.add_argument("--port-manifest", required=True, type=Path)
    port.add_argument("--out", type=Path)
    port.add_argument("--json", action="store_true")
    port.add_argument("--pretty", action="store_true")


def handle_certify(args: argparse.Namespace) -> int:
    try:
        if args.certify_command == "port":
            report = certify_port_manifest(args.port_manifest)
            if args.out:
                write_certification_report(report, args.out)
                print(f"Certification report written: {args.out}")
            print(render_json(report.to_dict(), pretty=args.pretty or args.json))
            return 0 if report.passed else 1
    except (OSError, ValueError) as exc:
        print(f"djlib-doctor certify: ERROR\n{exc}", file=sys.stderr)
        return 3
    raise ValueError(f"Unknown certify command: {args.certify_command}")
