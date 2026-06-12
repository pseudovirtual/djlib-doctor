from __future__ import annotations

import argparse

from .cli_parser import build_parser
from .cli_port import handle_migrate, handle_port
from .cli_read import (
    handle_apply_manifest,
    handle_compare,
    handle_config,
    handle_decision_sheet,
    handle_explain,
    handle_inspect,
    handle_plan,
    handle_review,
    handle_schema,
    handle_self_test,
    handle_snapshot,
    handle_verify,
)
from .cli_stage import handle_install, handle_stage


HANDLERS = {
    "verify": handle_verify,
    "snapshot": handle_snapshot,
    "plan": handle_plan,
    "explain": handle_explain,
    "decision-sheet": handle_decision_sheet,
    "review": handle_review,
    "apply-manifest": handle_apply_manifest,
    "schema": handle_schema,
    "config": handle_config,
    "inspect": handle_inspect,
    "stage": handle_stage,
    "install": handle_install,
    "migrate": handle_migrate,
    "self-test": handle_self_test,
    "port": handle_port,
    "compare": handle_compare,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = HANDLERS.get(args.command)
    if handler is None:
        parser.error(f"unknown command: {args.command}")
    try:
        return handler(args)
    except argparse.ArgumentError as exc:
        parser.error(str(exc))
    return 2
