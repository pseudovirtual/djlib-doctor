from __future__ import annotations

import argparse
import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from .cli_common import fail
from .port_rekordbox_serato import (
    build_rekordbox_collection_to_serato_plan,
    build_rekordbox_to_serato_plan,
    build_rekordbox_to_serato_plans,
    build_rekordbox_track_to_serato_plan,
    read_playlist_names,
    render_rekordbox_to_serato_summary,
    verify_rekordbox_to_serato_plan,
    write_rekordbox_to_serato_plan,
)
from .port_serato_rekordbox import (
    build_serato_collection_to_rekordbox_plan,
    build_serato_to_rekordbox_plan,
    build_serato_track_to_rekordbox_plan,
    write_serato_to_rekordbox_plan,
)
from .workflows import migrate_rekordbox_to_serato, migrate_serato_to_rekordbox


def handle_migrate(args: argparse.Namespace) -> int:
    if args.migrate_command == "rb-to-serato":
        _require_one_scope(args, ("playlist", "playlists_file", "track_id", "collection"))
        try:
            playlists = read_playlist_names(args.playlists_file) if args.playlists_file else ()
            result = migrate_rekordbox_to_serato(
                args.rekordbox_xml,
                playlist=args.playlist,
                playlists=playlists,
                track_id=args.track_id,
                collection=args.collection,
                out_dir=args.out,
                crate_prefix=args.crate_prefix,
                transfer_mode=args.transfer_mode,
                serato_library_dir=args.serato_library_dir,
                serato_music_dir=args.serato_music_dir,
                stage_library=args.stage_library,
                stage_tags=args.stage_tags,
            )
        except (ET.ParseError, OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            return fail("migrate", exc)
        print(f"Port manifest: {result.port_manifest}")
        for crate_path in result.crate_previews:
            print(f"Crate preview: {crate_path}")
        if result.serato_stage:
            print(f"Serato stage: {result.serato_stage.stage_manifest_path}")
            print(f"Serato install token: {result.serato_stage.install_token}")
        if result.tag_stage:
            print(f"Serato tag stage: {result.tag_stage.stage_manifest_path}")
            print(f"Serato tag install token: {result.tag_stage.install_token}")
        return 0
    return _migrate_serato_to_rb(args)


def _migrate_serato_to_rb(args: argparse.Namespace) -> int:
    try:
        _require_one_scope(args, ("crate", "portable_id", "collection"))
        result = migrate_serato_to_rekordbox(
            args.serato_library_dir,
            args.collection_root,
            args.out,
            args.crate,
            args.portable_id,
            args.collection,
            args.playlist_name,
            args.transfer_mode,
            args.rekordbox_db,
            args.stage_db,
        )
    except (OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return fail("migrate", exc)
    print(f"Port manifest: {result.port_manifest}")
    print(f"Rekordbox XML preview: {result.rekordbox_xml_preview}")
    if result.rekordbox_stage:
        print(f"Rekordbox DB stage: {result.rekordbox_stage.stage_manifest_path}")
        print(f"Rekordbox install token: {result.rekordbox_stage.install_token}")
    return 0


def handle_port(args: argparse.Namespace) -> int:
    if args.port_command == "rb-to-serato":
        return _port_rb_to_serato(args)
    try:
        plan = _build_serato_to_rb_from_args(args)
        outputs = write_serato_to_rekordbox_plan(plan, args.out)
    except (OSError, sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
        return fail("port", exc)
    print(f"Port manifest written: {outputs['manifest']}")
    print(f"Rekordbox XML preview written: {outputs['rekordbox_xml_preview']}")
    return 0


def _port_rb_to_serato(args: argparse.Namespace) -> int:
    _require_one_scope(args, ("playlist", "playlists_file", "track_id", "collection"))
    try:
        if args.track_id:
            plan = build_rekordbox_track_to_serato_plan(
                args.rekordbox_xml, args.track_id, args.crate_prefix, args.transfer_mode
            )
        elif args.collection:
            plan = build_rekordbox_collection_to_serato_plan(args.rekordbox_xml, args.crate_prefix, args.transfer_mode)
        elif args.playlists_file:
            playlist_names = read_playlist_names(args.playlists_file)
            if not playlist_names:
                raise ValueError(f"No playlist names found in {args.playlists_file}")
            plan = build_rekordbox_to_serato_plans(
                args.rekordbox_xml, playlist_names, args.crate_prefix, args.transfer_mode
            )
        else:
            plan = build_rekordbox_to_serato_plan(
                args.rekordbox_xml, args.playlist, args.crate_prefix, args.transfer_mode
            )
        if args.summary_only:
            print(render_rekordbox_to_serato_summary(plan))
            return 0
        outputs = write_rekordbox_to_serato_plan(plan, args.out)
        verification = _verify_preview(args, outputs)
    except (ET.ParseError, OSError, ValueError) as exc:
        return fail("port", exc)
    print(f"Port manifest written: {outputs['manifest']}")
    for crate_path in [outputs["crate_preview"]] if "crate_preview" in outputs else outputs["crate_previews"]:
        print(f"Serato crate preview written: {crate_path}")
    print(f"Unsupported report written: {outputs['unsupported_csv']}")
    if verification is not None:
        print(f"Preview verification: {'passed' if verification['passed'] else 'failed'}")
        return 0 if verification["passed"] else 1
    return 0


def _build_serato_to_rb_from_args(args: argparse.Namespace):
    _require_one_scope(args, ("crate", "portable_id", "collection"))
    if args.portable_id:
        return build_serato_track_to_rekordbox_plan(
            args.serato_library_dir, args.portable_id, args.collection_root, args.playlist_name, args.transfer_mode
        )
    if args.collection:
        return build_serato_collection_to_rekordbox_plan(
            args.serato_library_dir, args.collection_root, args.playlist_name, args.transfer_mode
        )
    return build_serato_to_rekordbox_plan(args.serato_library_dir, args.crate, args.collection_root, args.playlist_name)


def _require_one_scope(args: argparse.Namespace, names: tuple[str, ...]) -> None:
    selected = [name for name in names if bool(getattr(args, name))]
    if len(selected) != 1:
        flags = ", ".join("--" + name.replace("_", "-") for name in names)
        raise argparse.ArgumentError(None, f"exactly one scope is required: {flags}")


def _verify_preview(args: argparse.Namespace, outputs: dict[str, str]):
    if not args.verify_preview:
        return None
    crate_preview = outputs.get("crate_preview")
    if crate_preview is None:
        raise ValueError("--verify-preview currently supports single-playlist manifests")
    return verify_rekordbox_to_serato_plan(Path(outputs["manifest"]), Path(crate_preview))
