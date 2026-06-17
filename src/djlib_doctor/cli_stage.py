from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys

from .file_operations import apply_file_operations_stage, stage_file_operations
from .rekordbox_db_stage import install_rekordbox_db_stage, stage_rekordbox_db_import, stage_rekordbox_db_operations
from .serato_audio_tags import build_serato_audio_tag_stage, install_serato_audio_tag_stage
from .serato_stage import install_serato_stage, stage_serato_from_port_manifest


def _fail(label: str, exc: Exception) -> int:
    print(f"djlib-doctor {label}: ERROR\n{exc}", file=sys.stderr)
    return 3


def handle_stage(args: argparse.Namespace) -> int:
    try:
        if args.stage_command == "serato":
            report = stage_serato_from_port_manifest(args.port_manifest, args.serato_library_dir, args.serato_music_dir, args.stage_dir)
            print(f"Serato stage written: {report.stage_manifest_path}")
            print(f"Staged root.sqlite: {report.staged_root_sqlite}")
            for crate_path in report.crate_paths:
                print(f"Staged crate: {crate_path}")
        elif args.stage_command == "serato-tags":
            report = build_serato_audio_tag_stage(args.port_manifest, args.stage_dir)
            print(f"Serato audio tag stage written: {report.stage_manifest_path}")
            print(f"Tagged copies: {report.summary['tagged_copies']}")
        elif args.stage_command == "file-ops":
            report = stage_file_operations(args.operations, args.stage_dir)
            print(f"File operations stage written: {report.stage_manifest_path}")
        elif args.stage_command == "rekordbox-db":
            report = stage_rekordbox_db_operations(args.db, args.operations, args.stage_dir)
            print(f"Rekordbox DB stage written: {report.stage_manifest_path}")
            print(f"Staged DB: {report.staged_db}")
        elif args.stage_command == "rekordbox-db-import":
            report = stage_rekordbox_db_import(args.db, args.port_manifest, args.stage_dir)
            print(f"Rekordbox DB import stage written: {report.stage_manifest_path}")
            print(f"Staged DB: {report.staged_db}")
        else:
            raise ValueError(f"Unknown stage command: {args.stage_command}")
    except (OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return _fail("stage", exc)
    print(f"Install token: {report.install_token}")
    return 0


def handle_install(args: argparse.Namespace) -> int:
    try:
        if args.install_command == "serato-stage":
            lines = () if args.skip_process_check else _serato_process_lines()
            report = install_serato_stage(args.stage_dir, args.serato_library_dir, args.serato_music_dir, args.confirm_token, lines)
            print(f"Serato stage installed: {report.report_path}")
            print(f"Backup directory: {report.backup_dir}")
        elif args.install_command == "serato-tags":
            report = install_serato_audio_tag_stage(args.stage_dir, args.confirm_token)
            print(f"Serato audio tags installed: {args.stage_dir / 'serato-audio-tag-install-report.json'}")
            print(f"Tagged files installed: {len(report['installed'])}")
        elif args.install_command == "file-ops":
            report = apply_file_operations_stage(args.stage_dir, args.confirm_token, continue_on_error=args.continue_on_error)
            print(f"File operations applied: {args.stage_dir / 'file-operations-install-report.json'}")
            print(f"Operations applied: {len(report['applied'])}")
        elif args.install_command == "rekordbox-db":
            lines = () if args.skip_process_check else _app_process_lines("rekordbox|Rekordbox")
            report = install_rekordbox_db_stage(args.stage_dir, args.db, args.confirm_token, lines)
            print(f"Rekordbox DB stage installed: {args.stage_dir / 'rekordbox-db-install-report.json'}")
            print(f"Backup: {report['backup']}")
        else:
            raise ValueError(f"Unknown install command: {args.install_command}")
    except (OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return _fail("install", exc)
    return 0


def _serato_process_lines() -> tuple[str, ...]:
    return _app_process_lines("Serato|serato")


def _app_process_lines(pattern: str) -> tuple[str, ...]:
    try:
        result = subprocess.run(["pgrep", "-fl", pattern], check=False, capture_output=True, text=True)
    except OSError:
        return ()
    return tuple(line for line in result.stdout.splitlines() if line.strip()) if result.returncode in (0, 1) else ()
