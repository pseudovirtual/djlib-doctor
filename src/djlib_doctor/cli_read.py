from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

from .apply_manifest import build_apply_manifest, write_apply_manifest
from .collision_policy import get_duplicate_collision_policy
from .compare import compare_exports, write_compare_report
from .compatibility import customize_audio_compatibility_profile, get_audio_compatibility_profile, list_audio_compatibility_profiles
from .config import default_config, load_config, write_config
from .decision_sheet import write_decision_sheet
from .io_utils import render_json
from .plan import build_audio_compatibility_plan, build_bad_paths_plan, build_cues_plan, build_duplicates_plan, build_missing_files_plan, load_plan, write_plan
from .port_rekordbox_serato import build_rekordbox_to_serato_plan
from .rekordbox_xml import parse_rekordbox_xml
from .reviewer import load_review_log, run_interactive_review
from .schemas import render_schema
from .serato_sqlite import inspect_serato_root_sqlite, write_serato_inspection
from .snapshot import create_snapshot
from .verify import SCHEMA_VERSION as VERIFY_SCHEMA_VERSION
from .verify import verify_library


def _fail(label: str, exc: Exception) -> int:
    print(f"djlib-doctor {label}: ERROR\n{exc}", file=sys.stderr)
    return 3


def handle_verify(args: argparse.Namespace) -> int:
    if args.schema_version:
        print(VERIFY_SCHEMA_VERSION)
        return 0
    if args.xml is None:
        raise argparse.ArgumentError(None, "the following arguments are required: xml")
    try:
        library = parse_rekordbox_xml(args.xml)
    except (ET.ParseError, OSError, ValueError) as exc:
        return _fail("verification", exc)
    report = verify_library(library, check_files=not args.no_file_check, source_path=str(args.xml))
    rendered = report.render_json(pretty=args.pretty) if args.json else report.render_text()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
        print(f"Verification report written: {args.out}")
    print(rendered)
    return 0 if report.passed else 1


def handle_snapshot(args: argparse.Namespace) -> int:
    try:
        result = create_snapshot(args.rekordbox_xml, args.out, args.music_root, not args.no_file_check, args.redact_paths)
    except (ET.ParseError, OSError, ValueError) as exc:
        return _fail("snapshot", exc)
    print(f"Snapshot written: {result.snapshot_path}")
    print(result.report.render_text())
    return 0 if result.report.passed else 1


def handle_plan(args: argparse.Namespace) -> int:
    if args.plan_command == "audio-compatibility" and args.list_profiles:
        for profile in list_audio_compatibility_profiles():
            print(f"{profile.name}: {profile.description}")
        return 0
    try:
        report = _build_plan(args)
        write_plan(report, args.out)
    except (ET.ParseError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        return _fail("plan", exc)
    print(f"Plan written: {args.out}")
    print(report.render_text())
    return 0


def _build_plan(args: argparse.Namespace):
    if args.plan_command == "missing-files":
        return build_missing_files_plan(args.snapshot)
    if args.plan_command == "duplicates":
        return build_duplicates_plan(args.snapshot, collision_policy=get_duplicate_collision_policy(args.collision_policy))
    if args.plan_command == "bad-paths":
        markers = tuple(args.markers) if args.markers else None
        return build_bad_paths_plan(args.snapshot, markers=markers) if markers else build_bad_paths_plan(args.snapshot)
    if args.plan_command == "cues":
        return build_cues_plan(args.baseline, args.final)
    if args.plan_command == "audio-compatibility":
        if args.probe_csv is None or args.out is None:
            raise ValueError("--probe-csv and --out are required")
        profile = customize_audio_compatibility_profile(
            get_audio_compatibility_profile(args.profile),
            allowed_extensions=tuple(args.allowed_extensions) if args.allowed_extensions else None,
            allowed_codecs=tuple(args.allowed_codecs) if args.allowed_codecs else None,
            max_sample_rate_hz=args.max_sample_rate,
            max_bit_depth=args.max_bit_depth,
            warn_below_bit_rate_kbps=args.warn_below_bitrate,
        )
        return build_audio_compatibility_plan(args.probe_csv, profile=profile)
    raise ValueError(f"Unknown plan command: {args.plan_command}")


def handle_explain(args: argparse.Namespace) -> int:
    try:
        print(load_plan(args.plan).render_text())
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail("explain", exc)


def handle_decision_sheet(args: argparse.Namespace) -> int:
    try:
        write_decision_sheet(load_plan(args.plan), args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail("decision-sheet", exc)
    print(f"Decision sheet written: {args.out}")
    return 0


def handle_review(args: argparse.Namespace) -> int:
    try:
        run_interactive_review(load_plan(args.plan), args.out)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail("review", exc)


def handle_apply_manifest(args: argparse.Namespace) -> int:
    try:
        review_log = load_review_log(args.review_log) if args.review_log else None
        write_apply_manifest(build_apply_manifest(load_plan(args.plan), review_log, args.only_reviewed), args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail("apply-manifest", exc)
    print(f"Dry-run apply manifest written: {args.out}")
    return 0


def handle_schema(args: argparse.Namespace) -> int:
    try:
        print(render_schema(args.name, pretty=args.pretty))
        return 0
    except ValueError as exc:
        return _fail("schema", exc)


def handle_config(args: argparse.Namespace) -> int:
    try:
        if args.config_command == "init":
            config = default_config(
                rekordbox_xml=args.rekordbox_xml,
                rekordbox_db=args.rekordbox_db,
                serato_library_dir=args.serato_library_dir,
                serato_music_dir=args.serato_music_dir,
                music_root=args.music_root,
                crate_prefix=args.crate_prefix,
                primary=args.primary,
            )
            write_config(args.out, config)
            print(f"Config written: {args.out}")
        else:
            print(render_json(load_config(args.config), pretty=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail("config", exc)


def handle_inspect(args: argparse.Namespace) -> int:
    try:
        out_path = write_serato_inspection(inspect_serato_root_sqlite(args.library_dir / "root.sqlite"), args.out)
    except (OSError, sqlite3.Error, ValueError) as exc:
        return _fail("inspect", exc)
    print(f"Serato inspection written: {out_path}")
    return 0


def handle_self_test(args: argparse.Namespace) -> int:
    try:
        with TemporaryDirectory() as tmpdir:
            fixture = _write_self_test_fixture(Path(tmpdir))
            report = verify_library(parse_rekordbox_xml(fixture), check_files=False, source_path=str(fixture))
            build_rekordbox_to_serato_plan(fixture, "ROOT / Fixture Playlist")
    except Exception as exc:
        return _fail("self-test", exc)
    print("djlib-doctor self-test: PASS")
    print("Fixture: generated synthetic Rekordbox XML")
    print(f"Tracks: {report.collection_tracks}")
    return 0


def _write_self_test_fixture(tmpdir: Path) -> Path:
    fixture = tmpdir / "self-test-rekordbox.xml"
    fixture.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<DJ_PLAYLISTS Version="1.0.0">
  <COLLECTION Entries="1">
    <TRACK TrackID="1" Name="Self Test Track" Artist="Fixture Artist" TotalTime="120" Kind="AIFF File" Location="file://localhost/tmp/djlib-doctor-self-test.aiff">
      <POSITION_MARK Name="Hotcue A" Type="0" Start="24.000" Num="0"/>
    </TRACK>
  </COLLECTION>
  <PLAYLISTS>
    <NODE Type="0" Name="ROOT" Count="1">
      <NODE Name="Fixture Playlist" Type="1" KeyType="0" Entries="1">
        <TRACK Key="1"/>
      </NODE>
    </NODE>
  </PLAYLISTS>
</DJ_PLAYLISTS>
""",
        encoding="utf-8",
    )
    return fixture


def handle_compare(args: argparse.Namespace) -> int:
    try:
        report = compare_exports(args.baseline, args.final, check_files=args.check_files)
        if args.out:
            write_compare_report(report, args.out)
    except (ET.ParseError, OSError, ValueError) as exc:
        return _fail("compare", exc)
    print(report.render_json(pretty=args.pretty) if args.json else report.render_text())
    return 0 if report.passed else 1
