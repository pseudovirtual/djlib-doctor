from __future__ import annotations

import csv
from pathlib import Path

from .io_utils import write_json
from .port_rekordbox_serato_models import RekordboxToSeratoBatchPlan, RekordboxToSeratoPlan
from .serato_crate import safe_crate_filename, write_serato_crate


def write_rekordbox_to_serato_plan(
    plan: RekordboxToSeratoPlan | RekordboxToSeratoBatchPlan, out_dir: Path
) -> dict[str, str | list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "port-manifest.json"
    unsupported_path = out_dir / "unsupported.csv"
    write_json(manifest_path, plan.to_dict())
    if isinstance(plan, RekordboxToSeratoBatchPlan):
        crate_paths = []
        for crate_plan in plan.crates:
            crate_path = _unique_crate_path(out_dir, crate_plan.target_crate_name, crate_paths)
            write_serato_crate(crate_path, tuple(track.serato_portable_id for track in crate_plan.tracks))
            crate_paths.append(crate_path)
        _write_unsupported_csv(unsupported_path, plan)
        return {
            "manifest": str(manifest_path),
            "crate_previews": [str(path) for path in crate_paths],
            "unsupported_csv": str(unsupported_path),
        }
    crate_path = out_dir / f"{safe_crate_filename(plan.target_crate_name)}.crate"
    write_serato_crate(crate_path, tuple(track.serato_portable_id for track in plan.tracks))
    _write_unsupported_csv(unsupported_path, plan)
    return {"manifest": str(manifest_path), "crate_preview": str(crate_path), "unsupported_csv": str(unsupported_path)}


def read_playlist_names(path: Path) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def render_rekordbox_to_serato_summary(plan: RekordboxToSeratoPlan | RekordboxToSeratoBatchPlan) -> str:
    summary = plan.summary
    lines = [
        "Dry-run Serato summary",
        f"Crates: {summary.get('crates', 1)}",
        f"Tracks: {summary['tracks']}",
        f"Skipped: {summary['skipped']}",
        f"Cue intents: {summary['cue_intents']}",
        f"Warnings: {summary['warnings']}",
    ]
    for label, key in (("Formats", "format_counts"), ("Cue counts", "cue_counts")):
        counts = summary.get(key, {})
        if counts:
            lines.append(label + ": " + ", ".join(f"{name}={count}" for name, count in sorted(counts.items())))
    return "\n".join(lines)


def _write_unsupported_csv(path: Path, plan: RekordboxToSeratoPlan | RekordboxToSeratoBatchPlan) -> None:
    rows = []
    plans = plan.crates if isinstance(plan, RekordboxToSeratoBatchPlan) else (plan,)
    for crate_plan in plans:
        rows.extend(
            {"track_id": track.source_id, "artist": track.artist, "title": track.title, "issue": issue}
            for track in crate_plan.tracks
            for issue in track.unsupported
        )
        rows.extend(
            {
                "track_id": row.get("track_id", ""),
                "artist": row.get("artist", ""),
                "title": row.get("title", ""),
                "issue": row.get("reason", ""),
            }
            for row in crate_plan.skipped
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["track_id", "artist", "title", "issue"])
        writer.writeheader()
        writer.writerows(rows)


def _unique_crate_path(out_dir: Path, crate_name: str, existing_paths: list[Path]) -> Path:
    base = safe_crate_filename(crate_name)
    candidate = out_dir / f"{base}.crate"
    index = 2
    while candidate in set(existing_paths):
        candidate = out_dir / f"{base} ({index}).crate"
        index += 1
    return candidate
