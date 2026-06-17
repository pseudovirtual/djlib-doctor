from __future__ import annotations

import sys


def fail(label: str, exc: Exception) -> int:
    print(f"djlib-doctor {label}: ERROR\n{exc}", file=sys.stderr)
    return 3
