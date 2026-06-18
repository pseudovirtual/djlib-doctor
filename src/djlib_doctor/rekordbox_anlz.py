from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnlzCueTimes:
    time_ms: int
    loop_time_ms: int | None = None


@dataclass(frozen=True)
class AnlzBeatgridTimes:
    times_ms: tuple[int, ...]


def shift_anlz_cues(source: Path, target: Path, shift_ms: int) -> int:
    data = bytearray(source.read_bytes())
    changed = 0
    for entry in _cue_entries(data):
        _write_u32(data, entry[0], max(0, _read_u32(data, entry[0]) + shift_ms))
        if entry[1] is not None:
            value = _read_u32(data, entry[1])
            if value != 0xFFFFFFFF:
                _write_u32(data, entry[1], max(0, value + shift_ms))
        changed += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return changed


def read_anlz_cue_times(path: Path) -> tuple[AnlzCueTimes, ...]:
    data = bytearray(path.read_bytes())
    cues = []
    for time_offset, loop_offset in _cue_entries(data):
        loop_time = None if loop_offset is None else _read_u32(data, loop_offset)
        if loop_time == 0xFFFFFFFF:
            loop_time = None
        cues.append(AnlzCueTimes(_read_u32(data, time_offset), loop_time))
    return tuple(cues)


def _cue_entries(data: bytearray) -> list[tuple[int, int | None]]:
    if data[:4] != b"PMAI":
        raise ValueError("Unsupported ANLZ file header")
    file_len = _read_u32(data, 8)
    offset = _read_u32(data, 4)
    entries = []
    while offset + 12 <= min(file_len, len(data)):
        tag_type = bytes(data[offset : offset + 4])
        len_header = _read_u32(data, offset + 4)
        len_tag = _read_u32(data, offset + 8)
        if tag_type == b"PCOB":
            entries.extend(_pcob_entries(data, offset, len_header))
        elif tag_type == b"PCO2":
            entries.extend(_pco2_entries(data, offset, len_header))
        offset += len_tag
    return entries


def shift_anlz_beatgrids(source: Path, target: Path, shift_ms: int) -> int:
    data = bytearray(target.read_bytes() if target.exists() else source.read_bytes())
    changed = 0
    for offset in _beatgrid_offsets(data):
        _write_u32(data, offset, max(0, _read_u32(data, offset) + shift_ms))
        changed += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return changed


def read_anlz_beatgrid_times(path: Path) -> tuple[AnlzBeatgridTimes, ...]:
    data = bytearray(path.read_bytes())
    groups = []
    for offsets in _beatgrid_offset_groups(data):
        groups.append(AnlzBeatgridTimes(tuple(_read_u32(data, offset) for offset in offsets)))
    return tuple(groups)


def _beatgrid_offsets(data: bytearray) -> list[int]:
    offsets = []
    for group in _beatgrid_offset_groups(data):
        offsets.extend(group)
    return offsets


def _beatgrid_offset_groups(data: bytearray) -> list[tuple[int, ...]]:
    if data[:4] != b"PMAI":
        raise ValueError("Unsupported ANLZ file header")
    file_len = _read_u32(data, 8)
    offset = _read_u32(data, 4)
    groups = []
    while offset + 12 <= min(file_len, len(data)):
        tag_type = bytes(data[offset : offset + 4])
        len_tag = _read_u32(data, offset + 8)
        if tag_type == b"PQTZ":
            groups.append(tuple(_pqtz_offsets(data, offset)))
        elif tag_type == b"PQT2":
            groups.append(tuple(_pqt2_offsets(data, offset)))
        offset += len_tag
    return groups


def _pqtz_offsets(data: bytearray, tag_offset: int) -> list[int]:
    count = _read_u32(data, tag_offset + 20)
    return [tag_offset + 28 + index * 8 for index in range(count)]


def _pqt2_offsets(data: bytearray, tag_offset: int) -> list[int]:
    return [tag_offset + 28, tag_offset + 36]


def _pcob_entries(data: bytearray, tag_offset: int, len_header: int) -> list[tuple[int, int | None]]:
    count = _read_u16(data, tag_offset + 18)
    offset = tag_offset + len_header
    entries = []
    for _ in range(count):
        len_entry = _read_u32(data, offset + 8)
        entries.append((offset + 32, offset + 36))
        offset += len_entry
    return entries


def _pco2_entries(data: bytearray, tag_offset: int, len_header: int) -> list[tuple[int, int | None]]:
    count = _read_u16(data, tag_offset + 16)
    offset = tag_offset + len_header
    entries = []
    for _ in range(count):
        len_entry = _read_u32(data, offset + 8)
        entries.append((offset + 20, offset + 24))
        offset += len_entry
    return entries


def _read_u16(data: bytearray, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def _read_u32(data: bytearray, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def _write_u32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into(">I", data, offset, value)
