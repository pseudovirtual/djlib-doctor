from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .certify import CertificationReport, certify_port_manifest, write_certification_report
from .sync_common import required_path
from .workflows import migrate_rekordbox_to_serato, migrate_serato_to_rekordbox


@dataclass(frozen=True)
class SyncPlanResult:
    direction: str
    port_manifest: Path
    certification_path: Path
    certification: CertificationReport


def plan_sync(
    config: dict[str, Any],
    out_dir: Path,
    playlist: str | None = None,
    playlists: tuple[str, ...] = (),
    track_id: str | None = None,
    crate: Path | None = None,
    portable_id: str | None = None,
    collection: bool = False,
    playlist_name: str | None = None,
    transfer_mode: str = "full",
) -> SyncPlanResult:
    primary = config.get("primary", "rekordbox")
    if primary == "rekordbox":
        return _plan_rekordbox_primary(config, out_dir, playlist, playlists, track_id, collection, transfer_mode)
    if primary == "serato":
        return _plan_serato_primary(config, out_dir, crate, portable_id, collection, playlist_name, transfer_mode)
    raise ValueError("Config primary must be 'rekordbox' or 'serato'")


def _plan_rekordbox_primary(
    config: dict[str, Any],
    out_dir: Path,
    playlist: str | None,
    playlists: tuple[str, ...],
    track_id: str | None,
    collection: bool,
    transfer_mode: str,
) -> SyncPlanResult:
    rekordbox_xml = required_path(config, "rekordbox_xml")
    result = migrate_rekordbox_to_serato(
        rekordbox_xml=rekordbox_xml,
        out_dir=out_dir,
        playlist=playlist,
        playlists=playlists,
        track_id=track_id,
        collection=collection,
        transfer_mode=transfer_mode,
        crate_prefix=str(config.get("crate_prefix") or "RB - "),
    )
    return _certified("rb-to-serato", result.port_manifest, out_dir)


def _plan_serato_primary(
    config: dict[str, Any],
    out_dir: Path,
    crate: Path | None,
    portable_id: str | None,
    collection: bool,
    playlist_name: str | None,
    transfer_mode: str,
) -> SyncPlanResult:
    result = migrate_serato_to_rekordbox(
        serato_library_dir=required_path(config, "serato_library_dir"),
        collection_root=required_path(config, "music_root"),
        out_dir=out_dir,
        crate=crate,
        portable_id=portable_id,
        collection=collection,
        playlist_name=playlist_name,
        transfer_mode=transfer_mode,
    )
    return _certified("serato-to-rb", result.port_manifest, out_dir)


def _certified(direction: str, port_manifest: Path, out_dir: Path) -> SyncPlanResult:
    report = certify_port_manifest(port_manifest)
    certification_path = out_dir / "certification.json"
    write_certification_report(report, certification_path)
    return SyncPlanResult(direction, port_manifest, certification_path, report)
