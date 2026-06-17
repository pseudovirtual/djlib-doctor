from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .config import load_config
from .port_rekordbox_serato import read_playlist_names
from .sync_planner import plan_sync


def add_sync_parser(sub: argparse._SubParsersAction) -> None:
    sync = sub.add_parser("sync", help="Plan or run primary-library projection workflows.").add_subparsers(
        dest="sync_command", required=True
    )
    plan = sync.add_parser("plan", help="Create a dry-run port manifest and certification from config primary.")
    plan.add_argument("--config", required=True, type=Path)
    plan.add_argument("--out", required=True, type=Path)
    plan.add_argument("--playlist")
    plan.add_argument("--playlists-file", type=Path)
    plan.add_argument("--track-id")
    plan.add_argument("--crate", type=Path)
    plan.add_argument("--portable-id")
    plan.add_argument("--collection", action="store_true")
    plan.add_argument("--playlist-name")
    plan.add_argument("--transfer-mode", default="full", choices=("full", "cues-only", "match-only"))


def handle_sync(args: argparse.Namespace) -> int:
    try:
        if args.sync_command == "plan":
            playlists = read_playlist_names(args.playlists_file) if args.playlists_file else ()
            result = plan_sync(
                load_config(args.config),
                args.out,
                playlist=args.playlist,
                playlists=playlists,
                track_id=args.track_id,
                crate=args.crate,
                portable_id=args.portable_id,
                collection=args.collection,
                playlist_name=args.playlist_name,
                transfer_mode=args.transfer_mode,
            )
            print(f"Direction: {result.direction}")
            print(f"Port manifest: {result.port_manifest}")
            print(f"Certification: {result.certification_path}")
            return 0 if result.certification.passed else 1
    except (ET.ParseError, OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"djlib-doctor sync: ERROR\n{exc}", file=sys.stderr)
        return 3
    raise ValueError(f"Unknown sync command: {args.sync_command}")
