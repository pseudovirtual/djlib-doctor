from __future__ import annotations

from pathlib import Path
from typing import Any

from .serato_markers import build_markers2_payload, encode_markers2_geob_data

MP4_MARKERS2_KEY = "----:com.serato.dj:markersv2"


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
        _write_id3_audio(AIFF(path), track, payload, GEOB, TALB, TBPM, TCON, TKEY, TIT2, TPE1)
    elif suffix == ".mp3":
        _write_id3_audio(MP3(path), track, payload, GEOB, TALB, TBPM, TCON, TKEY, TIT2, TPE1)
    else:
        _write_mp4_audio(MP4(path), track, payload, MP4FreeForm, AtomDataType)


def _write_id3_audio(
    audio: Any,
    track: dict[str, Any],
    payload: bytes,
    GEOB: Any,
    TALB: Any,
    TBPM: Any,
    TCON: Any,
    TKEY: Any,
    TIT2: Any,
    TPE1: Any,
) -> None:
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


def _write_mp4_audio(audio: Any, track: dict[str, Any], payload: bytes, MP4FreeForm: Any, AtomDataType: Any) -> None:
    if audio.tags is None:
        audio.add_tags()
    audio.tags["\xa9nam"] = [str(track.get("title", ""))]
    if track.get("artist"):
        audio.tags["\xa9ART"] = [str(track.get("artist", ""))]
    audio.tags[MP4_MARKERS2_KEY] = [MP4FreeForm(payload, dataformat=AtomDataType.IMPLICIT)]
    audio.save()
