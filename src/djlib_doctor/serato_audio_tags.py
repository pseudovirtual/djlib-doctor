from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import struct
from typing import Any


SERATO_AUDIO_TAG_STAGE_SCHEMA_VERSION = "1.0"
SERATO_AUDIO_TAG_INSTALL_SCHEMA_VERSION = "1.0"
MP4_MARKERS2_KEY = "----:com.serato.dj:markersv2"

_VERSION = (2, 1)
_VERSION_FORMAT = ">2B"
_CUE_COLORS = (
    b"\xcc\x00\x00",
    b"\xcc\x88\x00",
    b"\xcc\xcc\x00",
    b"\x00\xcc\x00",
    b"\x00\xcc\xcc",
    b"\x00\x00\xcc",
    b"\x88\x00\xcc",
    b"\xcc\x00\x88",
)


@dataclass(frozen=True)
class SeratoAudioTagStageReport:
    stage_dir: Path
    stage_manifest_path: Path
    install_token: str
    summary: dict[str, Any]


def build_markers2_payload(cue_intents: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> bytes:
    contents = [struct.pack(_VERSION_FORMAT, *_VERSION)]
    for intent in cue_intents:
        slot = int(intent.get("slot") or 0)
        label = str(intent.get("label") or "")
        if intent.get("intent") == "serato_hotcue":
            contents.append(_named_entry("CUE", _cue_entry(slot, int(intent["start_ms"]), label)))
        elif intent.get("intent") == "serato_saved_loop":
            contents.append(
                _named_entry(
                    "LOOP",
                    _loop_entry(
                        slot,
                        int(intent["start_ms"]),
                        int(intent.get("end_ms") or intent["start_ms"]),
                        label,
                    ),
                )
            )
    return b"".join(contents)


def build_serato_audio_tag_stage(port_manifest_path: Path, stage_dir: Path) -> SeratoAudioTagStageReport:
    manifest = json.loads(port_manifest_path.read_text(encoding="utf-8"))
    tracks = _manifest_tracks(manifest)
    tagged_dir = stage_dir / "tagged-audio"
    tagged_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for track in tracks:
        rows.append(_stage_track_tag_copy(track, tagged_dir))
    hashes = {
        row["staged_path"]: row["staged_sha256"]
        for row in rows
        if row.get("staged_path") and row.get("staged_sha256")
    }
    install_token = _install_token(hashes)
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
        "install_token": install_token,
    }
    stage_manifest_path = stage_dir / "serato-audio-tag-stage-manifest.json"
    stage_manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return SeratoAudioTagStageReport(stage_dir, stage_manifest_path, install_token, summary)


def install_serato_audio_tag_stage(stage_dir: Path, confirm_token: str) -> dict[str, Any]:
    manifest_path = stage_dir / "serato-audio-tag-stage-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if confirm_token != manifest["install_token"]:
        raise ValueError("Confirmation token does not match staged audio-tag install token")
    backup_dir = stage_dir / "audio-tag-backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    installed = []
    for row in manifest["tracks"]:
        if row["status"] != "tagged_copy":
            continue
        source = Path(row["source_path"])
        staged = Path(row["staged_path"])
        if _sha256(staged) != row["staged_sha256"]:
            raise RuntimeError(f"Staged tagged audio hash mismatch: {staged}")
        backup = backup_dir / _backup_name(source)
        if not backup.exists():
            shutil.copy2(source, backup)
        shutil.copy2(staged, source)
        installed.append(
            {
                "source_path": str(source),
                "backup_path": str(backup),
                "staged_path": str(staged),
                "installed_sha256": _sha256(source),
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
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    staged = tagged_dir / _backup_name(source)
    shutil.copy2(source, staged)
    try:
        _write_tags(staged, track)
    except ImportError as exc:
        return {**base, "status": "unsupported_missing_dependency", "detail": str(exc)}
    return {
        **base,
        "status": "tagged_copy",
        "staged_path": str(staged),
        "staged_sha256": _sha256(staged),
    }


def _write_tags(path: Path, track: dict[str, Any]) -> None:
    try:
        from mutagen.aiff import AIFF
        from mutagen.id3 import GEOB, TALB, TBPM, TCON, TKEY, TIT2, TPE1
        from mutagen.mp3 import MP3
        from mutagen.mp4 import MP4, MP4FreeForm, AtomDataType
    except ImportError as exc:
        raise ImportError("Install djlib-doctor[audio-tags] to stage Serato audio tags") from exc

    payload = build_markers2_payload(track.get("cue_intents", ()))
    suffix = path.suffix.lower()
    if suffix in {".aiff", ".aif"}:
        audio = AIFF(path)
        if audio.tags is None:
            audio.add_tags()
        _write_id3_standard(audio.tags, track, TALB, TBPM, TCON, TKEY, TIT2, TPE1)
        audio.tags.setall("GEOB:Serato Markers2", [GEOB(encoding=0, mime="application/octet-stream", filename="Serato Markers2", desc="Serato Markers2", data=payload)])
        audio.save()
    elif suffix == ".mp3":
        audio = MP3(path)
        if audio.tags is None:
            audio.add_tags()
        _write_id3_standard(audio.tags, track, TALB, TBPM, TCON, TKEY, TIT2, TPE1)
        audio.tags.setall("GEOB:Serato Markers2", [GEOB(encoding=0, mime="application/octet-stream", filename="Serato Markers2", desc="Serato Markers2", data=payload)])
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


def _write_id3_standard(tags: Any, track: dict[str, Any], TALB: Any, TBPM: Any, TCON: Any, TKEY: Any, TIT2: Any, TPE1: Any) -> None:
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


def _cue_entry(index: int, position_ms: int, label: str) -> bytes:
    color = _CUE_COLORS[index % len(_CUE_COLORS)]
    return b"".join(
        (
            struct.pack(">cBIc3s2s", b"\x00", index, position_ms, b"\x00", color, b"\x00\x00"),
            label[:51].encode("utf-8"),
            b"\x00",
        )
    )


def _loop_entry(index: int, start_ms: int, end_ms: int, label: str) -> bytes:
    color = b"\xff" + _CUE_COLORS[index % len(_CUE_COLORS)]
    return b"".join(
        (
            struct.pack(">cBII4s4s3s?", b"\x00", index, start_ms, end_ms, b"\x00\x00\x00\x00", color, b"\x00\x00\x00", False),
            label[:51].encode("utf-8"),
            b"\x00",
        )
    )


def _named_entry(name: str, payload: bytes) -> bytes:
    return name.encode("utf-8") + b"\x00" + struct.pack(">I", len(payload)) + payload


def _install_token(hashes: dict[str, str]) -> str:
    payload = json.dumps(hashes, sort_keys=True).encode("utf-8")
    return f"INSTALL_SERATO_TAGS:{hashlib.sha256(payload).hexdigest()[:16]}"


def _backup_name(path: Path) -> str:
    safe_parent = "__".join(path.parent.parts[-3:])
    return f"{safe_parent}__{path.name}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
