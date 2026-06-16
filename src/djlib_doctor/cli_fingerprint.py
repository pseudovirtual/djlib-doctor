from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .fingerprint import compare_tracks, fingerprint_file, scan_fingerprints
from .io_utils import write_json


def add_fingerprint_parser(sub: argparse._SubParsersAction) -> None:
    fp = sub.add_parser("fingerprint", help="Fingerprint or compare local audio files.").add_subparsers(
        dest="fingerprint_command", required=True
    )
    one = fp.add_parser("file")
    one.add_argument("path", type=Path)
    one.add_argument("--out", type=Path)
    cmp = fp.add_parser("compare")
    cmp.add_argument("left", type=Path)
    cmp.add_argument("right", type=Path)
    cmp.add_argument("--out", type=Path)
    scan = fp.add_parser("scan")
    scan.add_argument("root", type=Path)
    scan.add_argument("--out", required=True, type=Path)
    scan.add_argument("--redact-paths", action="store_true")


def _fail(exc: Exception) -> int:
    print(f"djlib-doctor fingerprint: ERROR\n{exc}", file=sys.stderr)
    return 3


def handle_fingerprint(args: argparse.Namespace) -> int:
    try:
        if args.fingerprint_command == "file":
            data = fingerprint_file(args.path).to_dict()
            _write_or_print(data, args.out)
            return 0
        if args.fingerprint_command == "compare":
            data = compare_tracks(args.left, args.right).to_dict()
            _write_or_print(data, args.out)
            return 0
        if args.fingerprint_command == "scan":
            data = scan_fingerprints(args.root, redact_paths=args.redact_paths).to_dict()
            _write_or_print(data, args.out)
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail(exc)
    raise ValueError(f"Unknown fingerprint command: {args.fingerprint_command}")


def _write_or_print(data, out) -> None:
    if out:
        write_json(out, data)
        print(f"Fingerprint report written: {out}")
    else:
        print(json.dumps(data, indent=2, sort_keys=True))
