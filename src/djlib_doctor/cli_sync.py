from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .cli_stage import _app_process_lines, _serato_process_lines
from .config import load_config
from .port_rekordbox_serato import read_playlist_names
from .sync_planner import plan_sync
from .sync_runner import install_sync_plan


def add_sync_parser(sub: argparse._SubParsersAction) -> None:
    sync = sub.add_parser("sync", help="Plan or run primary-library projection workflows.")
    sync.add_argument("sync_command", nargs="?", choices=("plan", "run"), default="run")
    sync.add_argument("--config", required=True, type=Path)
    sync.add_argument("--out", required=True, type=Path)
    sync.add_argument("--playlist")
    sync.add_argument("--playlists-file", type=Path)
    sync.add_argument("--track-id")
    sync.add_argument("--crate", type=Path)
    sync.add_argument("--portable-id")
    sync.add_argument("--collection", action="store_true")
    sync.add_argument("--playlist-name")
    sync.add_argument("--transfer-mode", default="full", choices=("full", "cues-only", "match-only"))
    sync.add_argument("--apply", action="store_true")
    sync.add_argument("--yes", action="store_true")
    sync.add_argument("--confirm-token")
    sync.add_argument("--skip-process-check", action="store_true")


def handle_sync(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
        plan_kwargs = _plan_kwargs(args)
        if args.sync_command == "plan":
            result = plan_sync(config, args.out, **plan_kwargs)
            _print_plan(result)
            return 0 if result.certification.passed else 1
        plan = plan_sync(config, args.out, **plan_kwargs)
        _print_plan(plan)
        if not args.apply:
            print("Dry-run only. Re-run with --apply to stage and install.")
            return 0 if plan.certification.passed else 1
        _require_sync_approval(args)
        lines = () if args.skip_process_check else _process_lines(config)
        result = install_sync_plan(config, args.out, plan, install_token=args.confirm_token, process_lines=lines)
        print(f"Stage manifest: {result.stage_manifest}")
        print(f"Install report: {result.install_report}")
        return 0
    except (ET.ParseError, OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"djlib-doctor sync: ERROR\n{exc}", file=sys.stderr)
        return 3
    raise ValueError(f"Unknown sync command: {args.sync_command}")


def _plan_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {
        "playlist": args.playlist,
        "playlists": read_playlist_names(args.playlists_file) if args.playlists_file else (),
        "track_id": args.track_id,
        "crate": args.crate,
        "portable_id": args.portable_id,
        "collection": args.collection,
        "playlist_name": args.playlist_name,
        "transfer_mode": args.transfer_mode,
    }


def _print_plan(result) -> None:
    print(f"Direction: {result.direction}")
    print(f"Port manifest: {result.port_manifest}")
    print(f"Certification: {result.certification_path}")
    _print_preview_summary(result.certification.summary)


def _print_preview_summary(summary: dict[str, object]) -> None:
    print("Preview summary:")
    print(
        f"Tracks: matched {summary.get('matched_tracks', summary.get('tracks', 0))}, unmatched {summary.get('unmatched_tracks', summary.get('skipped', 0))}"
    )
    print(f"Cues: {summary.get('cues', 0)}, loops: {summary.get('loops', 0)}, playlists: {summary.get('playlists', 0)}")
    print(f"Unsupported rows: {summary.get('unsupported_rows', summary.get('unsupported_tracks', 0))}")


def _require_sync_approval(args: argparse.Namespace) -> None:
    if args.yes or args.confirm_token:
        return
    if not sys.stdin.isatty():
        raise ValueError("sync requires interactive stdin, --yes, or --confirm-token")
    if input("Type yes to stage and install this sync: ").strip().lower() != "yes":
        raise ValueError("sync cancelled")


def _process_lines(config: dict[str, object]) -> tuple[str, ...]:
    return (
        _serato_process_lines() if config.get("primary") == "rekordbox" else _app_process_lines("rekordbox|Rekordbox")
    )
