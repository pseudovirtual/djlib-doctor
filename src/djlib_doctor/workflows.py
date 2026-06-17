from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .port_rekordbox_serato import (
    build_rekordbox_collection_to_serato_plan,
    build_rekordbox_to_serato_plan,
    build_rekordbox_to_serato_plans,
    build_rekordbox_track_to_serato_plan,
    write_rekordbox_to_serato_plan,
)
from .port_serato_rekordbox import (
    build_serato_collection_to_rekordbox_plan,
    build_serato_to_rekordbox_plan,
    build_serato_track_to_rekordbox_plan,
    write_serato_to_rekordbox_plan,
)
from .rekordbox_db_stage import SqliteStage, stage_rekordbox_db_import
from .serato_audio_tags import SeratoAudioTagStageReport, build_serato_audio_tag_stage
from .serato_stage import SeratoStageReport, stage_serato_from_port_manifest


@dataclass(frozen=True)
class RekordboxToSeratoWorkflowResult:
    port_manifest: Path
    unsupported_csv: Path
    crate_previews: tuple[Path, ...]
    serato_stage: SeratoStageReport | None = None
    tag_stage: SeratoAudioTagStageReport | None = None


@dataclass(frozen=True)
class SeratoToRekordboxWorkflowResult:
    port_manifest: Path
    rekordbox_xml_preview: Path
    rekordbox_stage: SqliteStage | None = None


def migrate_rekordbox_to_serato(
    rekordbox_xml: Path,
    out_dir: Path,
    playlist: str | None = None,
    playlists: tuple[str, ...] = (),
    track_id: str | None = None,
    collection: bool = False,
    transfer_mode: str = "full",
    crate_prefix: str = "RB - ",
    serato_library_dir: Path | None = None,
    serato_music_dir: Path | None = None,
    stage_library: bool = False,
    stage_tags: bool = False,
) -> RekordboxToSeratoWorkflowResult:
    port_dir = out_dir / "port"
    if sum(bool(value) for value in (playlist, playlists, track_id, collection)) != 1:
        raise ValueError("Exactly one Rekordbox source scope is required")
    if track_id:
        plan = build_rekordbox_track_to_serato_plan(
            rekordbox_xml, track_id, crate_prefix=crate_prefix, transfer_mode=transfer_mode
        )
    elif collection:
        plan = build_rekordbox_collection_to_serato_plan(
            rekordbox_xml, crate_prefix=crate_prefix, transfer_mode=transfer_mode
        )
    elif playlists:
        plan = build_rekordbox_to_serato_plans(
            rekordbox_xml, playlists, crate_prefix=crate_prefix, transfer_mode=transfer_mode
        )
    elif playlist:
        plan = build_rekordbox_to_serato_plan(
            rekordbox_xml, playlist, crate_prefix=crate_prefix, transfer_mode=transfer_mode
        )
    else:
        raise ValueError("A Rekordbox source scope is required")
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


def migrate_serato_to_rekordbox(
    serato_library_dir: Path,
    collection_root: Path,
    out_dir: Path,
    crate: Path | None = None,
    portable_id: str | None = None,
    collection: bool = False,
    playlist_name: str | None = None,
    transfer_mode: str = "full",
    rekordbox_db: Path | None = None,
    stage_db: bool = False,
) -> SeratoToRekordboxWorkflowResult:
    if sum(bool(value) for value in (crate, portable_id, collection)) != 1:
        raise ValueError("Exactly one Serato source scope is required")
    if portable_id:
        plan = build_serato_track_to_rekordbox_plan(
            serato_library_dir, portable_id, collection_root, playlist_name, transfer_mode
        )
    elif collection:
        plan = build_serato_collection_to_rekordbox_plan(
            serato_library_dir, collection_root, playlist_name, transfer_mode
        )
    else:
        plan = build_serato_to_rekordbox_plan(serato_library_dir, crate, collection_root, playlist_name)
    outputs = write_serato_to_rekordbox_plan(plan, out_dir / "port")
    rekordbox_stage = None
    if stage_db:
        if rekordbox_db is None:
            raise ValueError("rekordbox_db is required when stage_db is true")
        rekordbox_stage = stage_rekordbox_db_import(
            rekordbox_db, Path(outputs["manifest"]), out_dir / "rekordbox-stage"
        )
    return SeratoToRekordboxWorkflowResult(
        port_manifest=Path(outputs["manifest"]),
        rekordbox_xml_preview=Path(outputs["rekordbox_xml_preview"]),
        rekordbox_stage=rekordbox_stage,
    )
