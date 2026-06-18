from __future__ import annotations

import argparse
from pathlib import Path


def add_stage_install_parser(sub: argparse._SubParsersAction) -> None:
    stage = sub.add_parser("stage").add_subparsers(dest="stage_command", required=True)
    _stage_serato(stage.add_parser("serato"))
    _stage_port_manifest(stage.add_parser("serato-tags"))
    _stage_file_ops(stage.add_parser("file-ops"))
    _stage_rekordbox_db(stage.add_parser("rekordbox-db"))
    _stage_rekordbox_db_import(stage.add_parser("rekordbox-db-import"))
    _stage_rekordbox_db_apply(stage.add_parser("rekordbox-db-apply"))

    install = sub.add_parser("install").add_subparsers(dest="install_command", required=True)
    _install_common(install.add_parser("serato-stage"), library=True)
    _install_common(install.add_parser("serato-tags"))
    file_ops = install.add_parser("file-ops")
    _install_common(file_ops)
    file_ops.add_argument("--continue-on-error", action="store_true")
    _install_common(install.add_parser("rekordbox-db"), db=True)


def _stage_serato(p: argparse.ArgumentParser) -> None:
    p.add_argument("--port-manifest", required=True, type=Path)
    p.add_argument("--serato-library-dir", required=True, type=Path)
    p.add_argument("--serato-music-dir", required=True, type=Path)
    p.add_argument("--stage-dir", required=True, type=Path)


def _stage_port_manifest(p: argparse.ArgumentParser) -> None:
    p.add_argument("--port-manifest", required=True, type=Path)
    p.add_argument("--stage-dir", required=True, type=Path)


def _stage_file_ops(p: argparse.ArgumentParser) -> None:
    p.add_argument("--operations", required=True, type=Path)
    p.add_argument("--stage-dir", required=True, type=Path)


def _stage_rekordbox_db(p: argparse.ArgumentParser) -> None:
    p.add_argument("--db", required=True, type=Path)
    p.add_argument("--operations", required=True, type=Path)
    p.add_argument("--stage-dir", required=True, type=Path)


def _stage_rekordbox_db_import(p: argparse.ArgumentParser) -> None:
    p.add_argument("--db", required=True, type=Path)
    p.add_argument("--port-manifest", required=True, type=Path)
    p.add_argument("--stage-dir", required=True, type=Path)


def _stage_rekordbox_db_apply(p: argparse.ArgumentParser) -> None:
    p.add_argument("--db", required=True, type=Path)
    p.add_argument("--apply-manifest", required=True, type=Path)
    p.add_argument("--stage-dir", required=True, type=Path)


def _install_common(p: argparse.ArgumentParser, library: bool = False, db: bool = False) -> None:
    p.add_argument("--stage-dir", required=True, type=Path)
    p.add_argument("--confirm-token", required=True)
    if library:
        p.add_argument("--serato-library-dir", required=True, type=Path)
        p.add_argument("--serato-music-dir", required=True, type=Path)
        p.add_argument("--skip-process-check", action="store_true")
    if db:
        p.add_argument("--db", required=True, type=Path)
        p.add_argument("--skip-process-check", action="store_true")
