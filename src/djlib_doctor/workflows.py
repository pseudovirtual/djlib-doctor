from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .port_serato import (
    build_rekordbox_to_serato_plan,
    build_rekordbox_to_serato_plans,
    write_rekordbox_to_serato_plan,
)
from .serato_audio_tags import SeratoAudioTagStageReport, build_serato_audio_tag_stage
from .serato_stage import SeratoStageReport, stage_serato_from_port_manifest


@dataclass(frozen=True)
class RekordboxToSeratoWorkflowResult:
    port_manifest: Path
    unsupported_csv: Path
    crate_previews: tuple[Path, ...]
    serato_stage: SeratoStageReport | None = None
    tag_stage: SeratoAudioTagStageReport | None = None


def migrate_rekordbox_to_serato(
    rekordbox_xml: Path,
    out_dir: Path,
    playlist: str | None = None,
    playlists: tuple[str, ...] = (),
    crate_prefix: str = "RB - ",
    serato_library_dir: Path | None = None,
    serato_music_dir: Path | None = None,
    stage_library: bool = False,
    stage_tags: bool = False,
) -> RekordboxToSeratoWorkflowResult:
    port_dir = out_dir / "port"
    if playlist and playlists:
        raise ValueError("Use either playlist or playlists, not both")
    if playlists:
        plan = build_rekordbox_to_serato_plans(rekordbox_xml, playlists, crate_prefix=crate_prefix)
    elif playlist:
        plan = build_rekordbox_to_serato_plan(rekordbox_xml, playlist, crate_prefix=crate_prefix)
    else:
        raise ValueError("A playlist or playlist list is required")
    outputs = write_rekordbox_to_serato_plan(plan, port_dir)
    crate_values = outputs.get("crate_previews") or [outputs["crate_preview"]]
    crate_previews = tuple(Path(value) for value in crate_values)
    port_manifest = Path(outputs["manifest"])
    serato_stage = None
    if stage_library:
        if serato_library_dir is None or serato_music_dir is None:
            raise ValueError("serato_library_dir and serato_music_dir are required when stage_library is true")
        serato_stage = stage_serato_from_port_manifest(
            port_manifest,
            serato_library_dir,
            serato_music_dir,
            out_dir / "serato-stage",
        )
    tag_stage = build_serato_audio_tag_stage(port_manifest, out_dir / "serato-tags") if stage_tags else None
    return RekordboxToSeratoWorkflowResult(
        port_manifest=port_manifest,
        unsupported_csv=Path(outputs["unsupported_csv"]),
        crate_previews=crate_previews,
        serato_stage=serato_stage,
        tag_stage=tag_stage,
    )
