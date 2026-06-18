from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def encode_audio(source: Path, staged: Path, preset: str) -> None:
    args = {
        "aac-m4a-128": ["-c:a", "aac", "-b:a", "128k"],
        "aac-m4a-256": ["-c:a", "aac", "-b:a", "256k"],
        "aiff-16": ["-c:a", "pcm_s16be"],
        "aiff-24": ["-c:a", "pcm_s24be"],
        "wav": ["-c:a", "pcm_s16le"],
    }.get(preset)
    if args is None:
        raise ValueError(f"Unsupported audio conversion preset: {preset}")
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), *args, str(staged)], check=True
    )


def encoder_delay_ms(encoded: Path) -> int:
    packets = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_packets",
                "-read_intervals",
                "%+#1",
                "-print_format",
                "json",
                str(encoded),
            ],
            text=True,
        )
    )
    sample_rate = _sample_rate(encoded)
    for packet in packets.get("packets", ()):
        for side_data in packet.get("side_data_list", ()):
            if side_data.get("side_data_type") == "Skip Samples":
                return round(int(side_data.get("skip_samples") or 0) * 1000 / sample_rate)
    return 0


def require_audio_tools() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for audio conversion staging")
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe is required for audio cue compensation")


def _sample_rate(encoded: Path) -> int:
    streams = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_streams",
                "-print_format",
                "json",
                str(encoded),
            ],
            text=True,
        )
    )
    return int(streams["streams"][0].get("sample_rate") or 44100)
