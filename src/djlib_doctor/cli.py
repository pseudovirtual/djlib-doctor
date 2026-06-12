from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET

from .apply_manifest import build_apply_manifest, write_apply_manifest
from .compatibility import (
    customize_audio_compatibility_profile,
    get_audio_compatibility_profile,
    list_audio_compatibility_profiles,
)
from .collision_policy import get_duplicate_collision_policy
from .compare import compare_exports, write_compare_report
from .decision_sheet import write_decision_sheet
from .file_operations import apply_file_operations_stage, stage_file_operations
from .plan import (
    build_audio_compatibility_plan,
    build_bad_paths_plan,
    build_cues_plan,
    build_duplicates_plan,
    build_missing_files_plan,
    load_plan,
    write_plan,
)
from .port_serato import (
    build_rekordbox_to_serato_plan,
    build_rekordbox_to_serato_plans,
    read_playlist_names,
    render_rekordbox_to_serato_summary,
    verify_rekordbox_to_serato_plan,
    write_rekordbox_to_serato_plan,
)
from .rekordbox_xml import parse_rekordbox_xml
from .reviewer import load_review_log, run_interactive_review
from .schemas import render_schema
from .serato_audio_tags import build_serato_audio_tag_stage, install_serato_audio_tag_stage
from .serato_sqlite import inspect_serato_root_sqlite, write_serato_inspection
from .serato_stage import install_serato_stage, stage_serato_from_port_manifest
from .sqlite_stage import install_sqlite_stage, stage_sqlite_operations
from .snapshot import create_snapshot
from .verify import SCHEMA_VERSION as VERIFY_SCHEMA_VERSION
from .verify import verify_library
from .workflows import migrate_rekordbox_to_serato


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="djlib-doctor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify", help="Verify a Rekordbox XML export without writing anything.")
    verify_parser.add_argument("xml", type=Path, nargs="?")
    verify_parser.add_argument(
        "--no-file-check",
        action="store_true",
        help="Parse and classify tracks without checking whether local paths exist.",
    )
    verify_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON verification report.",
    )
    verify_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output. Only applies with --json.",
    )
    verify_parser.add_argument(
        "--out",
        type=Path,
        help="Write the verification report to this file as text or JSON.",
    )
    verify_parser.add_argument(
        "--schema-version",
        action="store_true",
        help="Print the verification report schema version and exit.",
    )

    snapshot_parser = subparsers.add_parser("snapshot", help="Write a read-only snapshot directory for a Rekordbox XML export.")
    snapshot_parser.add_argument("--rekordbox-xml", required=True, type=Path)
    snapshot_parser.add_argument("--out", required=True, type=Path)
    snapshot_parser.add_argument("--music-root", type=Path)
    snapshot_parser.add_argument(
        "--no-file-check",
        action="store_true",
        help="Parse and classify tracks without checking whether local paths exist.",
    )
    snapshot_parser.add_argument(
        "--redact-paths",
        action="store_true",
        help="Redact source, local file, and inventory paths in snapshot artifacts for sharing.",
    )

    plan_parser = subparsers.add_parser("plan", help="Build a read-only cleanup plan from a snapshot.")
    plan_subparsers = plan_parser.add_subparsers(dest="plan_command", required=True)
    missing_parser = plan_subparsers.add_parser("missing-files", help="Plan review actions for missing local files.")
    missing_parser.add_argument("--snapshot", required=True, type=Path)
    missing_parser.add_argument("--out", required=True, type=Path)
    duplicates_parser = plan_subparsers.add_parser("duplicates", help="Plan review actions for duplicate collection records.")
    duplicates_parser.add_argument("--snapshot", required=True, type=Path)
    duplicates_parser.add_argument("--out", required=True, type=Path)
    duplicates_parser.add_argument(
        "--collision-policy",
        default="cue-safe",
        choices=("cue-safe", "quality", "keep-both"),
        help="How to choose duplicate survivors. Defaults to preserving cue-bearing records.",
    )
    bad_paths_parser = plan_subparsers.add_parser("bad-paths", help="Plan review actions for tracks pointing at bad/staging folders.")
    bad_paths_parser.add_argument("--snapshot", required=True, type=Path)
    bad_paths_parser.add_argument("--out", required=True, type=Path)
    bad_paths_parser.add_argument(
        "--marker",
        action="append",
        dest="markers",
        help="Folder-name marker to flag. Can be repeated; defaults cover trash/staging/temp/quarantine-style folders.",
    )
    compatibility_parser = plan_subparsers.add_parser(
        "audio-compatibility",
        help="Plan review actions from audio probe metadata CSV.",
    )
    compatibility_parser.add_argument("--probe-csv", type=Path)
    compatibility_parser.add_argument("--out", type=Path)
    compatibility_parser.add_argument(
        "--profile",
        default="rekordbox-conservative",
        help="Named compatibility profile. Use --list-profiles to see options.",
    )
    compatibility_parser.add_argument("--list-profiles", action="store_true", help="List audio compatibility profiles and exit.")
    compatibility_parser.add_argument("--allow-extension", action="append", dest="allowed_extensions", help="Allowed extension override, repeatable.")
    compatibility_parser.add_argument("--allow-codec", action="append", dest="allowed_codecs", help="Allowed codec override, repeatable.")
    compatibility_parser.add_argument("--max-sample-rate", type=int, help="Maximum allowed sample rate in Hz.")
    compatibility_parser.add_argument("--max-bit-depth", type=int, help="Maximum allowed bit depth.")
    compatibility_parser.add_argument("--warn-below-bitrate", type=int, help="Warn below this bit rate in kbps.")
    cues_parser = plan_subparsers.add_parser("cues", help="Plan review actions for cue coverage differences between exports.")
    cues_parser.add_argument("--baseline", required=True, type=Path)
    cues_parser.add_argument("--final", required=True, type=Path)
    cues_parser.add_argument("--out", required=True, type=Path)

    explain_parser = subparsers.add_parser("explain", help="Explain a generated plan.")
    explain_parser.add_argument("--plan", required=True, type=Path)

    decision_parser = subparsers.add_parser("decision-sheet", help="Write a human review CSV from a generated plan.")
    decision_parser.add_argument("--plan", required=True, type=Path)
    decision_parser.add_argument("--out", required=True, type=Path)

    review_parser = subparsers.add_parser("review", help="Interactively review a generated plan and record decisions.")
    review_parser.add_argument("--plan", required=True, type=Path)
    review_parser.add_argument("--out", required=True, type=Path)

    manifest_parser = subparsers.add_parser("apply-manifest", help="Write a dry-run-only apply manifest from a generated plan.")
    manifest_parser.add_argument("--plan", required=True, type=Path)
    manifest_parser.add_argument("--out", required=True, type=Path)
    manifest_parser.add_argument("--review-log", type=Path, help="Review decision log produced by `djlib-doctor review`.")
    manifest_parser.add_argument("--only-reviewed", action="store_true", help="Include only actions present in the review log.")

    schema_parser = subparsers.add_parser("schema", help="Print report and CSV schema metadata.")
    schema_parser.add_argument("name", nargs="?", help="Optional schema name.")
    schema_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect DJ library storage without writing to it.")
    inspect_subparsers = inspect_parser.add_subparsers(dest="inspect_command", required=True)
    inspect_serato_parser = inspect_subparsers.add_parser("serato", help="Inspect Serato root.sqlite schema and row counts.")
    inspect_serato_parser.add_argument("--library-dir", required=True, type=Path, help="Serato Library directory containing root.sqlite.")
    inspect_serato_parser.add_argument("--out", required=True, type=Path)

    stage_parser = subparsers.add_parser("stage", help="Create staged changes from reviewed dry-run manifests.")
    stage_subparsers = stage_parser.add_subparsers(dest="stage_command", required=True)
    stage_serato_parser = stage_subparsers.add_parser("serato", help="Stage a Serato library update from a port manifest.")
    stage_serato_parser.add_argument("--port-manifest", required=True, type=Path)
    stage_serato_parser.add_argument("--serato-library-dir", required=True, type=Path, help="Live Serato Library directory containing root.sqlite.")
    stage_serato_parser.add_argument("--serato-music-dir", required=True, type=Path, help="Live _Serato_ directory.")
    stage_serato_parser.add_argument("--stage-dir", required=True, type=Path)
    stage_tags_parser = stage_subparsers.add_parser("serato-tags", help="Stage Serato audio tag writes from a port manifest.")
    stage_tags_parser.add_argument("--port-manifest", required=True, type=Path)
    stage_tags_parser.add_argument("--stage-dir", required=True, type=Path)
    stage_file_ops_parser = stage_subparsers.add_parser("file-ops", help="Stage file copy/move/delete/convert operations from a manifest.")
    stage_file_ops_parser.add_argument("--operations", required=True, type=Path)
    stage_file_ops_parser.add_argument("--stage-dir", required=True, type=Path)
    stage_rb_db_parser = stage_subparsers.add_parser("rekordbox-db", help="Stage structured Rekordbox SQLite row operations.")
    stage_rb_db_parser.add_argument("--db", required=True, type=Path)
    stage_rb_db_parser.add_argument("--operations", required=True, type=Path)
    stage_rb_db_parser.add_argument("--stage-dir", required=True, type=Path)

    install_parser = subparsers.add_parser("install", help="Install a verified stage with explicit confirmation.")
    install_subparsers = install_parser.add_subparsers(dest="install_command", required=True)
    install_serato_parser = install_subparsers.add_parser("serato-stage", help="Install a verified Serato stage into live Serato paths.")
    install_serato_parser.add_argument("--stage-dir", required=True, type=Path)
    install_serato_parser.add_argument("--serato-library-dir", required=True, type=Path)
    install_serato_parser.add_argument("--serato-music-dir", required=True, type=Path)
    install_serato_parser.add_argument("--confirm-token", required=True)
    install_serato_parser.add_argument("--skip-process-check", action="store_true", help="Skip local pgrep app-closed check; intended for synthetic tests only.")
    install_tags_parser = install_subparsers.add_parser("serato-tags", help="Install staged Serato audio tag file copies.")
    install_tags_parser.add_argument("--stage-dir", required=True, type=Path)
    install_tags_parser.add_argument("--confirm-token", required=True)
    install_file_ops_parser = install_subparsers.add_parser("file-ops", help="Apply a staged file operation manifest.")
    install_file_ops_parser.add_argument("--stage-dir", required=True, type=Path)
    install_file_ops_parser.add_argument("--confirm-token", required=True)
    install_rb_db_parser = install_subparsers.add_parser("rekordbox-db", help="Install a staged Rekordbox SQLite DB copy.")
    install_rb_db_parser.add_argument("--stage-dir", required=True, type=Path)
    install_rb_db_parser.add_argument("--db", required=True, type=Path)
    install_rb_db_parser.add_argument("--confirm-token", required=True)

    migrate_parser = subparsers.add_parser("migrate", help="Run guided multi-step migration workflows.")
    migrate_subparsers = migrate_parser.add_subparsers(dest="migrate_command", required=True)
    migrate_rb_serato = migrate_subparsers.add_parser("rb-to-serato", help="Plan and optionally stage a Rekordbox XML to Serato migration.")
    migrate_rb_serato.add_argument("--rekordbox-xml", required=True, type=Path)
    migrate_rb_serato.add_argument("--playlist")
    migrate_rb_serato.add_argument("--playlists-file", type=Path)
    migrate_rb_serato.add_argument("--out", required=True, type=Path)
    migrate_rb_serato.add_argument("--crate-prefix", default="RB - ")
    migrate_rb_serato.add_argument("--serato-library-dir", type=Path)
    migrate_rb_serato.add_argument("--serato-music-dir", type=Path)
    migrate_rb_serato.add_argument("--stage-library", action="store_true")
    migrate_rb_serato.add_argument("--stage-tags", action="store_true")

    self_test_parser = subparsers.add_parser("self-test", help="Run a fast built-in smoke test using synthetic fixtures.")

    port_parser = subparsers.add_parser("port", help="Build dry-run migration plans between DJ library platforms.")
    port_subparsers = port_parser.add_subparsers(dest="port_command", required=True)
    rb_to_serato_parser = port_subparsers.add_parser("rb-to-serato", help="Plan a Rekordbox XML playlist as a Serato crate preview.")
    rb_to_serato_parser.add_argument("--rekordbox-xml", required=True, type=Path)
    rb_to_serato_parser.add_argument("--playlist", help="Rekordbox playlist path/name to plan.")
    rb_to_serato_parser.add_argument("--playlists-file", type=Path, help="Text file with one Rekordbox playlist path/name per line.")
    rb_to_serato_parser.add_argument("--out", required=True, type=Path)
    rb_to_serato_parser.add_argument("--crate-prefix", default="RB - ")
    rb_to_serato_parser.add_argument("--summary-only", action="store_true", help="Print a dry-run summary without writing files.")
    rb_to_serato_parser.add_argument("--verify-preview", action="store_true", help="Verify generated single-crate preview order against the manifest.")

    compare_parser = subparsers.add_parser("compare", help="Compare two Rekordbox XML exports without writing to either.")
    compare_subparsers = compare_parser.add_subparsers(dest="compare_command", required=True)
    exports_parser = compare_subparsers.add_parser("exports", help="Compare baseline and final Rekordbox XML exports.")
    exports_parser.add_argument("--baseline", required=True, type=Path)
    exports_parser.add_argument("--final", required=True, type=Path)
    exports_parser.add_argument("--out", type=Path)
    exports_parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    exports_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output. Only applies with --json.")
    exports_parser.add_argument("--check-files", action="store_true", help="Check whether final-export local paths exist.")

    args = parser.parse_args(argv)

    if args.command == "verify":
        if args.schema_version:
            print(VERIFY_SCHEMA_VERSION)
            return 0
        if args.xml is None:
            verify_parser.error("the following arguments are required: xml")
        try:
            library = parse_rekordbox_xml(args.xml)
        except (ET.ParseError, OSError, ValueError) as exc:
            print(f"djlib-doctor verification: ERROR\n{exc}", file=sys.stderr)
            return 3
        report = verify_library(library, check_files=not args.no_file_check, source_path=str(args.xml))
        rendered = report.render_json(pretty=args.pretty) if args.json else report.render_text()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(rendered + "\n", encoding="utf-8")
            print(f"Verification report written: {args.out}")
        if args.json:
            print(rendered)
        else:
            print(rendered)
        return 0 if report.passed else 1

    if args.command == "snapshot":
        try:
            result = create_snapshot(
                rekordbox_xml=args.rekordbox_xml,
                out_dir=args.out,
                music_root=args.music_root,
                check_files=not args.no_file_check,
                redact_paths=args.redact_paths,
            )
        except (ET.ParseError, OSError, ValueError) as exc:
            print(f"djlib-doctor snapshot: ERROR\n{exc}", file=sys.stderr)
            return 3
        print(f"Snapshot written: {result.snapshot_path}")
        print(result.report.render_text())
        return 0 if result.report.passed else 1

    if args.command == "plan":
        if args.plan_command == "missing-files":
            try:
                report = build_missing_files_plan(args.snapshot)
                write_plan(report, args.out)
            except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor plan: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Plan written: {args.out}")
            print(report.render_text())
            return 0
        if args.plan_command == "cues":
            try:
                report = build_cues_plan(args.baseline, args.final)
                write_plan(report, args.out)
            except (ET.ParseError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor plan: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Plan written: {args.out}")
            print(report.render_text())
            return 0
        if args.plan_command == "duplicates":
            try:
                report = build_duplicates_plan(args.snapshot, collision_policy=get_duplicate_collision_policy(args.collision_policy))
                write_plan(report, args.out)
            except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor plan: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Plan written: {args.out}")
            print(report.render_text())
            return 0
        if args.plan_command == "bad-paths":
            try:
                markers = tuple(args.markers) if args.markers else None
                report = build_bad_paths_plan(args.snapshot, markers=markers) if markers else build_bad_paths_plan(args.snapshot)
                write_plan(report, args.out)
            except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor plan: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Plan written: {args.out}")
            print(report.render_text())
            return 0
        if args.plan_command == "audio-compatibility":
            if args.list_profiles:
                for profile in list_audio_compatibility_profiles():
                    print(f"{profile.name}: {profile.description}")
                return 0
            if args.probe_csv is None:
                compatibility_parser.error("the following arguments are required: --probe-csv")
            if args.out is None:
                compatibility_parser.error("the following arguments are required: --out")
            try:
                profile = customize_audio_compatibility_profile(
                    get_audio_compatibility_profile(args.profile),
                    allowed_extensions=tuple(args.allowed_extensions) if args.allowed_extensions else None,
                    allowed_codecs=tuple(args.allowed_codecs) if args.allowed_codecs else None,
                    max_sample_rate_hz=args.max_sample_rate,
                    max_bit_depth=args.max_bit_depth,
                    warn_below_bit_rate_kbps=args.warn_below_bitrate,
                )
                report = build_audio_compatibility_plan(args.probe_csv, profile=profile)
                write_plan(report, args.out)
            except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor plan: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Plan written: {args.out}")
            print(report.render_text())
            return 0

    if args.command == "explain":
        try:
            report = load_plan(args.plan)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"djlib-doctor explain: ERROR\n{exc}", file=sys.stderr)
            return 3
        print(report.render_text())
        return 0

    if args.command == "decision-sheet":
        try:
            report = load_plan(args.plan)
            write_decision_sheet(report, args.out)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"djlib-doctor decision-sheet: ERROR\n{exc}", file=sys.stderr)
            return 3
        print(f"Decision sheet written: {args.out}")
        return 0

    if args.command == "review":
        try:
            report = load_plan(args.plan)
            run_interactive_review(report, args.out)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"djlib-doctor review: ERROR\n{exc}", file=sys.stderr)
            return 3
        return 0

    if args.command == "apply-manifest":
        try:
            report = load_plan(args.plan)
            review_log = load_review_log(args.review_log) if args.review_log else None
            manifest = build_apply_manifest(report, review_log=review_log, only_reviewed=args.only_reviewed)
            write_apply_manifest(manifest, args.out)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"djlib-doctor apply-manifest: ERROR\n{exc}", file=sys.stderr)
            return 3
        print(f"Dry-run apply manifest written: {args.out}")
        return 0

    if args.command == "schema":
        try:
            print(render_schema(args.name, pretty=args.pretty))
        except ValueError as exc:
            print(f"djlib-doctor schema: ERROR\n{exc}", file=sys.stderr)
            return 3
        return 0

    if args.command == "inspect":
        if args.inspect_command == "serato":
            try:
                inspection = inspect_serato_root_sqlite(args.library_dir / "root.sqlite")
                out_path = write_serato_inspection(inspection, args.out)
            except (OSError, sqlite3.Error, ValueError) as exc:
                print(f"djlib-doctor inspect: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Serato inspection written: {out_path}")
            return 0

    if args.command == "stage":
        if args.stage_command == "serato":
            try:
                report = stage_serato_from_port_manifest(
                    args.port_manifest,
                    args.serato_library_dir,
                    args.serato_music_dir,
                    args.stage_dir,
                )
            except (OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor stage: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Serato stage written: {report.stage_manifest_path}")
            print(f"Staged root.sqlite: {report.staged_root_sqlite}")
            for crate_path in report.crate_paths:
                print(f"Staged crate: {crate_path}")
            print(f"Install token: {report.install_token}")
            return 0
        if args.stage_command == "serato-tags":
            try:
                report = build_serato_audio_tag_stage(args.port_manifest, args.stage_dir)
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor stage: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Serato audio tag stage written: {report.stage_manifest_path}")
            print(f"Tagged copies: {report.summary['tagged_copies']}")
            print(f"Install token: {report.install_token}")
            return 0
        if args.stage_command == "file-ops":
            try:
                report = stage_file_operations(args.operations, args.stage_dir)
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor stage: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"File operations stage written: {report.stage_manifest_path}")
            print(f"Install token: {report.install_token}")
            return 0
        if args.stage_command == "rekordbox-db":
            try:
                report = stage_sqlite_operations(args.db, args.operations, args.stage_dir, label="rekordbox")
            except (OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor stage: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Rekordbox DB stage written: {report.stage_manifest_path}")
            print(f"Staged DB: {report.staged_db}")
            print(f"Install token: {report.install_token}")
            return 0

    if args.command == "install":
        if args.install_command == "serato-stage":
            try:
                process_lines = () if args.skip_process_check else _serato_process_lines()
                report = install_serato_stage(
                    args.stage_dir,
                    args.serato_library_dir,
                    args.serato_music_dir,
                    confirm_token=args.confirm_token,
                    process_lines=process_lines,
                )
            except (OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor install: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Serato stage installed: {report.report_path}")
            print(f"Backup directory: {report.backup_dir}")
            return 0
        if args.install_command == "serato-tags":
            try:
                report = install_serato_audio_tag_stage(args.stage_dir, confirm_token=args.confirm_token)
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor install: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Serato audio tags installed: {args.stage_dir / 'serato-audio-tag-install-report.json'}")
            print(f"Tagged files installed: {len(report['installed'])}")
            return 0
        if args.install_command == "file-ops":
            try:
                report = apply_file_operations_stage(args.stage_dir, confirm_token=args.confirm_token)
            except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor install: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"File operations applied: {args.stage_dir / 'file-operations-install-report.json'}")
            print(f"Operations applied: {len(report['applied'])}")
            return 0
        if args.install_command == "rekordbox-db":
            try:
                report = install_sqlite_stage(args.stage_dir, args.db, confirm_token=args.confirm_token, label="rekordbox")
            except (OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor install: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Rekordbox DB stage installed: {args.stage_dir / 'rekordbox-sqlite-install-report.json'}")
            print(f"Backup: {report['backup']}")
            return 0

    if args.command == "migrate":
        if args.migrate_command == "rb-to-serato":
            if bool(args.playlist) == bool(args.playlists_file):
                migrate_rb_serato.error("exactly one of --playlist or --playlists-file is required")
            try:
                playlists = read_playlist_names(args.playlists_file) if args.playlists_file else ()
                result = migrate_rekordbox_to_serato(
                    rekordbox_xml=args.rekordbox_xml,
                    playlist=args.playlist,
                    playlists=playlists,
                    out_dir=args.out,
                    crate_prefix=args.crate_prefix,
                    serato_library_dir=args.serato_library_dir,
                    serato_music_dir=args.serato_music_dir,
                    stage_library=args.stage_library,
                    stage_tags=args.stage_tags,
                )
            except (ET.ParseError, OSError, sqlite3.Error, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                print(f"djlib-doctor migrate: ERROR\n{exc}", file=sys.stderr)
                return 3
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

    if args.command == "self-test":
        fixture = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "rekordbox" / "simple.xml"
        try:
            library = parse_rekordbox_xml(fixture)
            report = verify_library(library, check_files=False, source_path=str(fixture))
            build_rekordbox_to_serato_plan(fixture, "ROOT / Fixture Playlist")
        except Exception as exc:
            print(f"djlib-doctor self-test: ERROR\n{exc}", file=sys.stderr)
            return 3
        print("djlib-doctor self-test: PASS")
        print(f"Fixture: {fixture}")
        print(f"Tracks: {report.collection_tracks}")
        return 0

    if args.command == "port":
        if args.port_command == "rb-to-serato":
            if bool(args.playlist) == bool(args.playlists_file):
                rb_to_serato_parser.error("exactly one of --playlist or --playlists-file is required")
            try:
                if args.playlists_file:
                    playlist_names = read_playlist_names(args.playlists_file)
                    if not playlist_names:
                        raise ValueError(f"No playlist names found in {args.playlists_file}")
                    plan = build_rekordbox_to_serato_plans(args.rekordbox_xml, playlist_names, crate_prefix=args.crate_prefix)
                else:
                    plan = build_rekordbox_to_serato_plan(args.rekordbox_xml, args.playlist, crate_prefix=args.crate_prefix)
                if args.summary_only:
                    print(render_rekordbox_to_serato_summary(plan))
                    return 0
                outputs = write_rekordbox_to_serato_plan(plan, args.out)
                verification = None
                if args.verify_preview:
                    crate_preview = outputs.get("crate_preview")
                    if crate_preview is None:
                        raise ValueError("--verify-preview currently supports single-playlist manifests")
                    verification = verify_rekordbox_to_serato_plan(Path(outputs["manifest"]), Path(crate_preview))
            except (ET.ParseError, OSError, ValueError) as exc:
                print(f"djlib-doctor port: ERROR\n{exc}", file=sys.stderr)
                return 3
            print(f"Port manifest written: {outputs['manifest']}")
            if "crate_preview" in outputs:
                print(f"Serato crate preview written: {outputs['crate_preview']}")
            else:
                for crate_path in outputs["crate_previews"]:
                    print(f"Serato crate preview written: {crate_path}")
            print(f"Unsupported report written: {outputs['unsupported_csv']}")
            if verification is not None:
                status = "passed" if verification["passed"] else "failed"
                print(f"Preview verification: {status}")
                return 0 if verification["passed"] else 1
            return 0

    if args.command == "compare":
        if args.compare_command == "exports":
            try:
                report = compare_exports(args.baseline, args.final, check_files=args.check_files)
                if args.out:
                    write_compare_report(report, args.out)
            except (ET.ParseError, OSError, ValueError) as exc:
                print(f"djlib-doctor compare: ERROR\n{exc}", file=sys.stderr)
                return 3
            if args.json:
                print(report.render_json(pretty=args.pretty))
            else:
                if args.out:
                    print(f"Compare report written: {args.out}")
                print(report.render_text())
            return 0 if report.passed else 1

    parser.error(f"unknown command: {args.command}")
    return 2


def _serato_process_lines() -> tuple[str, ...]:
    try:
        result = subprocess.run(
            ["pgrep", "-fl", "Serato|serato"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ()
    if result.returncode not in (0, 1):
        return ()
    return tuple(line for line in result.stdout.splitlines() if line.strip())


if __name__ == "__main__":
    raise SystemExit(main())
