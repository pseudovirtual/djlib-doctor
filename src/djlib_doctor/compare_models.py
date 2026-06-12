from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .io_utils import render_json

COMPARE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class CompareIssue:
    code: str
    message: str
    artist: str = ""
    title: str = ""
    playlist: str = ""
    path: str = ""

    def to_dict(self) -> dict[str, str]:
        data = {"code": self.code, "message": self.message}
        for key in ("artist", "title", "playlist", "path"):
            value = getattr(self, key)
            if value:
                data[key] = value
        return data


@dataclass(frozen=True)
class CompareReport:
    issues: tuple[CompareIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": COMPARE_SCHEMA_VERSION,
            "status": "pass" if self.passed else "fail",
            "summary": {code: sum(1 for issue in self.issues if issue.code == code) for code in ("missing_material", "cue_not_covered", "hotcue_regression", "playlist_order_or_entry_diff", "final_missing_local_file", "final_bad_path")} | {"issues": len(self.issues)},
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def render_json(self, pretty: bool = False) -> str:
        return render_json(self.to_dict(), pretty=pretty)

    def render_text(self) -> str:
        lines = [f"djlib-doctor compare: {'PASS' if self.passed else 'FAIL'}", f"Issues: {len(self.issues)}"]
        lines.extend(f"- {issue.code}: {issue.message}" for issue in self.issues)
        return "\n".join(lines)
