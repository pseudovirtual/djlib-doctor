from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="djlib-doctor", allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    _add_verify(sub)
    _add_snapshot(sub)
    _add_plan(sub)
    _add_review(sub)
    _add_schema_config_inspect(sub)
    _add_stage_install(sub)
    _add_migrate_port_compare(sub)
    sub.add_parser("self-test", help="Run a fast built-in smoke test using synthetic fixtures.")
    return parser


def _add_verify(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("verify", help="Verify a Rekordbox XML export without writing anything.")
    p.add_argument("xml", type=Path, nargs="?")
    p.add_argument("--no-file-check", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--schema-version", action="store_true")


def _add_snapshot(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("snapshot", help="Write a read-only snapshot directory.")
    p.add_argument("--rekordbox-xml", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--music-root", type=Path)
    p.add_argument("--no-file-check", action="store_true")
    p.add_argument("--redact-paths", action="store_true")


def _add_plan(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("plan", help="Build a read-only cleanup plan.")
    plans = p.add_subparsers(dest="plan_command", required=True)
    for name in ("missing-files", "duplicates", "bad-paths"):
        child = plans.add_parser(name)
        child.add_argument("--snapshot", required=True, type=Path)
        child.add_argument("--out", required=True, type=Path)
    plans.choices["duplicates"].add_argument("--collision-policy", default="cue-safe", choices=("cue-safe", "quality", "keep-both"))
    plans.choices["bad-paths"].add_argument("--marker", action="append", dest="markers")
    audio = plans.add_parser("audio-compatibility")
    audio.add_argument("--probe-csv", type=Path)
    audio.add_argument("--out", type=Path)
    audio.add_argument("--profile", default="rekordbox-conservative")
    audio.add_argument("--list-profiles", action="store_true")
    audio.add_argument("--allow-extension", action="append", dest="allowed_extensions")
    audio.add_argument("--allow-codec", action="append", dest="allowed_codecs")
    audio.add_argument("--max-sample-rate", type=int)
    audio.add_argument("--max-bit-depth", type=int)
    audio.add_argument("--warn-below-bitrate", type=int)
    cues = plans.add_parser("cues")
    cues.add_argument("--baseline", required=True, type=Path)
    cues.add_argument("--final", required=True, type=Path)
    cues.add_argument("--out", required=True, type=Path)


def _add_review(sub: argparse._SubParsersAction) -> None:
    for name in ("explain", "decision-sheet", "review"):
        p = sub.add_parser(name)
        p.add_argument("--plan", required=True, type=Path)
        if name != "explain":
            p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("apply-manifest")
    p.add_argument("--plan", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--review-log", type=Path)
    p.add_argument("--only-reviewed", action="store_true")


def _add_schema_config_inspect(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("schema")
    p.add_argument("name", nargs="?")
    p.add_argument("--pretty", action="store_true")
    cfg = sub.add_parser("config").add_subparsers(dest="config_command", required=True)
    init = cfg.add_parser("init")
    for arg in ("--rekordbox-xml", "--serato-library-dir", "--serato-music-dir", "--music-root"):
        init.add_argument(arg, type=Path)
    init.add_argument("--out", required=True, type=Path)
    init.add_argument("--crate-prefix", default="RB - ")
    show = cfg.add_parser("show")
    show.add_argument("--config", required=True, type=Path)
    inspect = sub.add_parser("inspect").add_subparsers(dest="inspect_command", required=True)
    serato = inspect.add_parser("serato")
    serato.add_argument("--library-dir", required=True, type=Path)
    serato.add_argument("--out", required=True, type=Path)


def _add_stage_install(sub: argparse._SubParsersAction) -> None:
    stage = sub.add_parser("stage").add_subparsers(dest="stage_command", required=True)
    serato = stage.add_parser("serato")
    serato.add_argument("--port-manifest", required=True, type=Path)
    serato.add_argument("--serato-library-dir", required=True, type=Path)
    serato.add_argument("--serato-music-dir", required=True, type=Path)
    serato.add_argument("--stage-dir", required=True, type=Path)
    tags = stage.add_parser("serato-tags")
    tags.add_argument("--port-manifest", required=True, type=Path)
    tags.add_argument("--stage-dir", required=True, type=Path)
    ops = stage.add_parser("file-ops")
    ops.add_argument("--operations", required=True, type=Path)
    ops.add_argument("--stage-dir", required=True, type=Path)
    db = stage.add_parser("rekordbox-db")
    db.add_argument("--db", required=True, type=Path)
    db.add_argument("--operations", required=True, type=Path)
    db.add_argument("--stage-dir", required=True, type=Path)
    db_import = stage.add_parser("rekordbox-db-import")
    db_import.add_argument("--db", required=True, type=Path)
    db_import.add_argument("--port-manifest", required=True, type=Path)
    db_import.add_argument("--stage-dir", required=True, type=Path)
    install = sub.add_parser("install").add_subparsers(dest="install_command", required=True)
    _install_common(install.add_parser("serato-stage"), library=True)
    _install_common(install.add_parser("serato-tags"))
    _install_common(install.add_parser("file-ops"))
    _install_common(install.add_parser("rekordbox-db"), db=True)


def _install_common(p: argparse.ArgumentParser, library: bool = False, db: bool = False) -> None:
    p.add_argument("--stage-dir", required=True, type=Path)
    p.add_argument("--confirm-token", required=True)
    if library:
        p.add_argument("--serato-library-dir", required=True, type=Path)
        p.add_argument("--serato-music-dir", required=True, type=Path)
        p.add_argument("--skip-process-check", action="store_true")
    if db:
        p.add_argument("--db", required=True, type=Path)


def _add_migrate_port_compare(sub: argparse._SubParsersAction) -> None:
    mig = sub.add_parser("migrate").add_subparsers(dest="migrate_command", required=True)
    rb = mig.add_parser("rb-to-serato")
    _rb_to_serato_args(rb)
    rb.add_argument("--stage-library", action="store_true")
    rb.add_argument("--stage-tags", action="store_true")
    rb.add_argument("--serato-library-dir", type=Path)
    rb.add_argument("--serato-music-dir", type=Path)
    srb = mig.add_parser("serato-to-rb")
    _serato_to_rb_args(srb)
    srb.add_argument("--stage-db", action="store_true")
    srb.add_argument("--rekordbox-db", type=Path)
    port = sub.add_parser("port").add_subparsers(dest="port_command", required=True)
    rbp = port.add_parser("rb-to-serato")
    _rb_to_serato_args(rbp)
    rbp.add_argument("--summary-only", action="store_true")
    rbp.add_argument("--verify-preview", action="store_true")
    _serato_to_rb_args(port.add_parser("serato-to-rb"))
    cmp = sub.add_parser("compare").add_subparsers(dest="compare_command", required=True).add_parser("exports")
    cmp.add_argument("--baseline", required=True, type=Path)
    cmp.add_argument("--final", required=True, type=Path)
    cmp.add_argument("--out", type=Path)
    cmp.add_argument("--json", action="store_true")
    cmp.add_argument("--pretty", action="store_true")
    cmp.add_argument("--check-files", action="store_true")


def _rb_to_serato_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--rekordbox-xml", required=True, type=Path)
    p.add_argument("--playlist")
    p.add_argument("--playlists-file", type=Path)
    p.add_argument("--track-id")
    p.add_argument("--collection", action="store_true")
    p.add_argument("--transfer-mode", default="full", choices=("full", "cues-only", "match-only"))
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--crate-prefix", default="RB - ")


def _serato_to_rb_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--serato-library-dir", required=True, type=Path)
    p.add_argument("--crate", type=Path)
    p.add_argument("--portable-id")
    p.add_argument("--collection", action="store_true")
    p.add_argument("--collection-root", required=True, type=Path)
    p.add_argument("--playlist-name")
    p.add_argument("--transfer-mode", default="full", choices=("full", "cues-only", "match-only"))
    p.add_argument("--out", required=True, type=Path)
