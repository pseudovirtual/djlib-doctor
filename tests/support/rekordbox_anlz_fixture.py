from __future__ import annotations

import struct
from pathlib import Path


def write_anlz_fixture(path: Path, cue_tag: bytes, time_ms: int, loop_ms: int) -> None:
    # Device-export ANLZ may contain PCOB/PCO2 cue entries; local libraries
    # usually store user cues in master.db and leave these cue lists empty.
    cue_payload = _pcob_payload(time_ms, loop_ms) if cue_tag == b"PCOB" else _pco2_payload(time_ms, loop_ms)
    _write_anlz(path, [_tag_bytes(cue_tag, 24 if cue_tag == b"PCOB" else 20, cue_payload)])


def write_empty_cue_anlz_fixture(path: Path, cue_tag: bytes) -> None:
    # Real local ANLZ keeps PCOB/PCO2 containers with zero PCPT/PCP2 cue rows;
    # PQTZ/PQT2 beat times are absolute milliseconds.
    cue_payload = _empty_pcob_payload() if cue_tag == b"PCOB" else _empty_pco2_payload()
    _write_anlz(path, [_tag_bytes(cue_tag, 24 if cue_tag == b"PCOB" else 20, cue_payload)])


def _write_anlz(path: Path, cue_tags: list[bytes]) -> None:
    tags = cue_tags
    tags.append(_tag_bytes(b"PQTZ", 24, _pqtz_payload((500, 1000, 1500))))
    tags.append(_tag_bytes(b"PQT2", 56, _pqt2_payload((250, 750))))
    body = b"".join(tags)
    header = b"PMAI" + struct.pack(">IIIIII", 28, 28 + len(body), 0, 0, 0, 0)
    path.write_bytes(header + body)


def _tag_bytes(name: bytes, len_header: int, payload: bytes) -> bytes:
    return name + struct.pack(">II", len_header, 12 + len(payload)) + payload


def _pcob_payload(time_ms: int, loop_ms: int) -> bytes:
    entry = (
        b"PCPT"
        + struct.pack(">IIIIIHHBBHII", 56, 56, 1, 4, 0x10000, 0xFFFF, 0xFFFF, 2, 0, 1000, time_ms, loop_ms)
        + b"\0" * 16
    )
    return struct.pack(">IHHI", 1, 0, 1, 0) + entry


def _pco2_payload(time_ms: int, loop_ms: int) -> bytes:
    comment = b"\0\0"
    entry = (
        b"PCP2"
        + struct.pack(">IIIB3xII", 56, 56, 1, 2, time_ms, loop_ms)
        + b"\0"
        + b"\0" * 7
        + struct.pack(">HHI", 0, 0, len(comment))
        + comment
        + b"\0\0\0\0"
        + b"\0" * 2
    )
    return struct.pack(">IHH", 1, 1, 0) + entry


def _empty_pcob_payload() -> bytes:
    return struct.pack(">IHHI", 0, 0, 0, 0)


def _empty_pco2_payload() -> bytes:
    return struct.pack(">IHH", 1, 0, 0)


def _pqtz_payload(times_ms: tuple[int, ...]) -> bytes:
    entries = b"".join(struct.pack(">HHI", index + 1, 12000, time_ms) for index, time_ms in enumerate(times_ms))
    return struct.pack(">III", 0x80000, 0, len(times_ms)) + entries


def _pqt2_payload(times_ms: tuple[int, int]) -> bytes:
    bpm_entries = b"".join(struct.pack(">HHI", index + 1, 12000, time_ms) for index, time_ms in enumerate(times_ms))
    return struct.pack(">III", 0, 0x01000002, 0) + bpm_entries + struct.pack(">IIII", 0, 0, 0, 0)
