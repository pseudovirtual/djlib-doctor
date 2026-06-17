from __future__ import annotations

import sys
from typing import Callable

CommandRunner = Callable[[list[str]], int]
InputFunc = Callable[[str], str]


def handle_menu(run_command: CommandRunner, input_func: Callable[[str], str] | None = None) -> int:
    if input_func is None and not sys.stdin.isatty():
        print(
            "djlib-doctor menu requires interactive stdin. Run `djlib-doctor doctor` or another command directly.",
            file=sys.stderr,
        )
        return 3
    ask = input_func or input
    while True:
        _print_menu()
        choice = ask("Choice: ").strip().lower()
        if choice in {"q", "quit", "5"}:
            return 0
        if choice in {"doctor", "1"}:
            return run_command(["doctor"])
        if choice in {"sync", "2"}:
            return _run_sync_plan(run_command, ask)
        if choice in {"fix", "3"}:
            return _run_fix_review(run_command, ask)
        if choice in {"config", "4"}:
            return _run_config_init(run_command, ask)
        print("Choose doctor, sync, fix, config, or quit.")


def _print_menu() -> None:
    print("djlib-doctor")
    print("1. doctor")
    print("2. sync")
    print("3. fix")
    print("4. config")
    print("5. quit")


def _run_sync_plan(run_command: CommandRunner, ask: InputFunc) -> int:
    config = _ask_default(ask, "Config path", "djlib-doctor.json")
    out = _ask_default(ask, "Output dir", "sync-plan")
    return run_command(["sync", "plan", "--config", config, "--collection", "--out", out])


def _run_config_init(run_command: CommandRunner, ask: InputFunc) -> int:
    out = _ask_default(ask, "Config output", "djlib-doctor.json")
    return run_command(["config", "init", "--out", out])


def _run_fix_review(run_command: CommandRunner, ask: InputFunc) -> int:
    snapshot = _ask_required(ask, "Snapshot path")
    if not snapshot:
        print("Fix needs a snapshot. Run `djlib-doctor snapshot ...` first.")
        return 3
    plan = _ask_default(ask, "Plan output", "missing-files-plan.json")
    review = _ask_default(ask, "Review log output", "review-decisions.json")
    plan_status = run_command(["plan", "missing-files", "--snapshot", snapshot, "--out", plan])
    if plan_status:
        return plan_status
    return run_command(["review", "--plan", plan, "--out", review])


def _ask_default(ask: InputFunc, label: str, default: str) -> str:
    value = ask(f"{label} [{default}]: ").strip()
    return value or default


def _ask_required(ask: InputFunc, label: str) -> str:
    return ask(f"{label}: ").strip()
