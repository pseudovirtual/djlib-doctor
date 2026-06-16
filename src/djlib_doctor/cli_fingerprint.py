from __future__ import annotations

import argparse
import json
import sys

from .fingerprint import compare_tracks, fingerprint_file
from .io_utils import write_json


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
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail(exc)
    raise ValueError(f"Unknown fingerprint command: {args.fingerprint_command}")


def _write_or_print(data, out) -> None:
    if out:
        write_json(out, data)
        print(f"Fingerprint report written: {out}")
    else:
        print(json.dumps(data, indent=2, sort_keys=True))
