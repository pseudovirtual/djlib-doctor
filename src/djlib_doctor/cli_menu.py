from __future__ import annotations

import sys
from typing import Callable


CommandRunner = Callable[[list[str]], int]


def handle_menu(run_command: CommandRunner, input_func: Callable[[str], str] | None = None) -> int:
    if input_func is None and not sys.stdin.isatty():
        print("djlib-doctor menu requires interactive stdin. Run `djlib-doctor doctor` or another command directly.", file=sys.stderr)
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
            print("Run: djlib-doctor sync plan --config run/djlib-doctor.json --collection --out run/sync-plan")
            return 0
        if choice in {"fix", "3"}:
            print("Run: djlib-doctor doctor")
            return 0
        if choice in {"config", "4"}:
            print("Run: djlib-doctor config init --out run/djlib-doctor.json")
            return 0
        print("Choose doctor, sync, fix, config, or quit.")


def _print_menu() -> None:
    print("djlib-doctor")
    print("1. doctor")
    print("2. sync")
    print("3. fix")
    print("4. config")
    print("5. quit")
