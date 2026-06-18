from __future__ import annotations

import argparse


def add_examples_parser(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("examples", help="Print common CLI and Python API examples.")


def handle_examples(args: argparse.Namespace) -> int:
    del args
    print(EXAMPLES_TEXT)
    return 0


EXAMPLES_TEXT = """djlib-doctor examples

CLI:
  djlib-doctor verify export.xml
  djlib-doctor snapshot --rekordbox-xml export.xml --out run/check --redact-paths
  djlib-doctor port serato-to-rb --serato-library-dir /path/to/serato --crate /path/to/_Serato_/Subcrates/My.crate --collection-root ~/Music --out run/serato-to-rb
  djlib-doctor stage rekordbox-db-import --db /path/to/rekordbox/master.db --port-manifest run/serato-to-rb/port-manifest.json --stage-dir run/rekordbox-stage

Python API:
  from djlib_doctor.rekordbox_xml import parse_rekordbox_xml
  from djlib_doctor.verify import verify_library
  from djlib_doctor.plan import build_missing_files_plan

More: docs/api-examples.md
"""
