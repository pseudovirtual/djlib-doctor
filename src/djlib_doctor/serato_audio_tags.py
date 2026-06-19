from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json
from .serato_markers import build_markers2_payload, encode_markers2_geob_data
from .stage_common import backup_name, install_token, sha256_file
from .stage_installer import copy_required_backup, require_file_hashes, require_stage_token

SERATO_AUDIO_TAG_STAGE_SCHEMA_VERSION = "1.0"
SERATO_AUDIO_TAG_INSTALL_SCHEMA_VERSION = "1.0"
MP4_MARKERS2_KEY = "----:com.serato.dj:markersv2"


@dataclass(frozen=True)
class SeratoAudioTagStageReport:
    stage_dir: Path
    stage_manifest_path: Path
    install_token: str
    summary: dict[str, Any]


def build_serato_audio_tag_stage(port_manifest_path: Path, stage_dir: Path) -> SeratoAudioTagStageReport:
    manifest = read_json(port_manifest_path)
    tracks = _manifest_tracks(manifest)
    tagged_dir = stage_dir / "tagged-audio"
    tagged_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for track in tracks:
        rows.append(_stage_track_tag_copy(track, tagged_dir))
    hashes = {
        row["staged_path"]: row["staged_sha256"] for row in rows if row.get("staged_path") and row.get("staged_sha256")
    }
    source_hashes = {
        row["source_path"]: row["source_sha256"] for row in rows if row.get("source_path") and row.get("source_sha256")
    }
    token = install_token("INSTALL_SERATO_TAGS", _install_token_payload(hashes, source_hashes))
    summary = {
        "tracks": len(rows),
        "tagged_copies": sum(1 for row in rows if row["status"] == "tagged_copy"),
        "unsupported": sum(1 for row in rows if row["status"].startswith("unsupported")),
        "source_missing": sum(1 for row in rows if row["status"] == "source_missing"),
    }
    data = {
        "schema_version": SERATO_AUDIO_TAG_STAGE_SCHEMA_VERSION,
        "mode": "staged_serato_audio_tags",
        "safety": {
            "writes_live_audio_files": False,
            "requires_install_command": True,
        },
        "source_port_manifest": str(port_manifest_path),
        "summary": summary,
        "tracks": rows,
        "hashes": hashes,
        "source_hashes": source_hashes,
        "install_token": token,
    }
    stage_manifest_path = stage_dir / "serato-audio-tag-stage-manifest.json"
    write_json(stage_manifest_path, data)
    return SeratoAudioTagStageReport(stage_dir, stage_manifest_path, token, summary)


def install_serato_audio_tag_stage(stage_dir: Path, confirm_token: str) -> dict[str, Any]:
    manifest_path = stage_dir / "serato-audio-tag-stage-manifest.json"
    manifest = read_json(manifest_path)
    require_stage_token(
        "INSTALL_SERATO_TAGS",
        _install_token_payload(manifest["hashes"], manifest["source_hashes"]),
        manifest["install_token"],
        confirm_token,
    )
    backup_dir = stage_dir / "audio-tag-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    installed = []
    for row in manifest["tracks"]:
        if row["status"] != "tagged_copy":
            continue
        source = Path(row["source_path"])
        staged = Path(row["staged_path"])
        require_file_hashes(
            [
                (staged, row["staged_sha256"], "Staged tagged audio"),
                (source, row["source_sha256"], "Live audio source"),
            ]
        )
        backup = backup_dir / backup_name(source)
        if not backup.exists():
            copy_required_backup(source, backup)
        shutil.copy2(staged, source)
        installed.append(
            {
                "source_path": str(source),
                "backup_path": str(backup),
                "staged_path": str(staged),
                "installed_sha256": sha256_file(source),
            }
        )
    report = {
        "schema_version": SERATO_AUDIO_TAG_INSTALL_SCHEMA_VERSION,
        "passed": True,
        "stage_manifest": str(manifest_path),
        "backup_dir": str(backup_dir),
        "installed": installed,
    }
    report_path = stage_dir / "serato-audio-tag-install-report.json"
    write_json(report_path, report)
    return report


def _stage_track_tag_copy(track: dict[str, Any], tagged_dir: Path) -> dict[str, Any]:
    source = Path(str(track.get("path", "")))
    base = {
        "track_id": str(track.get("source_id", "")),
        "artist": str(track.get("artist", "")),
        "title": str(track.get("title", "")),
        "source_path": str(source),
    }
    if not source.is_file():
        return {**base, "status": "source_missing"}
    suffix = source.suffix.lower()
    if suffix not in {".aiff", ".aif", ".m4a", ".mp4", ".mp3"}:
        return {**base, "status": f"unsupported_format:{suffix.lstrip('.') or 'unknown'}"}
    staged = tagged_dir / backup_name(source)
    shutil.copy2(source, staged)
    try:
        _write_tags(staged, track)
    except ImportError as exc:
        return {**base, "status": "unsupported_missing_dependency", "detail": str(exc)}
    return {
        **base,
        "status": "tagged_copy",
        "staged_path": str(staged),
        "source_sha256": sha256_file(source),
        "staged_sha256": sha256_file(staged),
    }


def _write_tags(path: Path, track: dict[str, Any]) -> None:
    try:
        from mutagen.aiff import AIFF
        from mutagen.id3 import GEOB, TALB, TBPM, TCON, TIT2, TKEY, TPE1
        from mutagen.mp3 import MP3
        from mutagen.mp4 import MP4, AtomDataType, MP4FreeForm
    except ImportError as exc:
        raise ImportError("Install djlib-doctor[audio-tags] to stage Serato audio tags") from exc
    payload = encode_markers2_geob_data(build_markers2_payload(track.get("cue_intents", ())))
    suffix = path.suffix.lower()
    if suffix in {".aiff", ".aif"}:
        audio = AIFF(path)
        if audio.tags is None:
            audio.add_tags()
        _write_id3_standard(audio.tags, track, TALB, TBPM, TCON, TKEY, TIT2, TPE1)
        audio.tags.setall(
            "GEOB:Serato Markers2",
            [
                GEOB(
                    encoding=0,
                    mime="application/octet-stream",
                    filename="Serato Markers2",
                    desc="Serato Markers2",
                    data=payload,
                )
            ],
        )
        audio.save()
    elif suffix == ".mp3":
        audio = MP3(path)
        if audio.tags is None:
            audio.add_tags()
        _write_id3_standard(audio.tags, track, TALB, TBPM, TCON, TKEY, TIT2, TPE1)
        audio.tags.setall(
            "GEOB:Serato Markers2",
            [
                GEOB(
                    encoding=0,
                    mime="application/octet-stream",
                    filename="Serato Markers2",
                    desc="Serato Markers2",
                    data=payload,
                )
            ],
        )
        audio.save()
    else:
        audio = MP4(path)
        if audio.tags is None:
            audio.add_tags()
        audio.tags["\xa9nam"] = [str(track.get("title", ""))]
        if track.get("artist"):
            audio.tags["\xa9ART"] = [str(track.get("artist", ""))]
        audio.tags[MP4_MARKERS2_KEY] = [MP4FreeForm(payload, dataformat=AtomDataType.IMPLICIT)]
        audio.save()


def _write_id3_standard(
    tags: Any, track: dict[str, Any], TALB: Any, TBPM: Any, TCON: Any, TKEY: Any, TIT2: Any, TPE1: Any
) -> None:
    tags.setall("TIT2", [TIT2(encoding=3, text=str(track.get("title", "")))])
    if track.get("artist"):
        tags.setall("TPE1", [TPE1(encoding=3, text=str(track.get("artist", "")))])
    if track.get("album"):
        tags.setall("TALB", [TALB(encoding=3, text=str(track.get("album", "")))])
    if track.get("genre"):
        tags.setall("TCON", [TCON(encoding=3, text=str(track.get("genre", "")))])
    if track.get("bpm"):
        tags.setall("TBPM", [TBPM(encoding=3, text=str(track.get("bpm", "")))])
    if track.get("key"):
        tags.setall("TKEY", [TKEY(encoding=3, text=str(track.get("key", "")))])


def _manifest_tracks(manifest: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if "crates" in manifest:
        tracks: list[dict[str, Any]] = []
        seen_paths = set()
        for crate in manifest["crates"]:
            for track in crate.get("tracks", ()):
                path = track.get("path", "")
                if path not in seen_paths:
                    tracks.append(track)
                    seen_paths.add(path)
        return tuple(tracks)
    return tuple(manifest.get("tracks", ()))


def _install_token_payload(hashes: dict[str, str], source_hashes: dict[str, str]) -> dict[str, Any]:
    return {"hashes": hashes, "source_hashes": source_hashes}
