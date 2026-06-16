from __future__ import annotations

import struct


def record(tag: str, payload: bytes) -> bytes:
    if len(tag) != 4:
        raise ValueError(f"Serato tags must be four characters: {tag}")
    return tag.encode("ascii") + struct.pack(">I", len(payload)) + payload


def parse_records(data: bytes) -> tuple[tuple[str, bytes], ...]:
    records = []
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Truncated Serato record header")
        tag = data[offset : offset + 4].decode("ascii")
        length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        offset += 8
        payload = data[offset : offset + length]
        if len(payload) != length:
            raise ValueError(f"Truncated Serato record payload: {tag}")
        records.append((tag, payload))
        offset += length
    return tuple(records)


def text(value: str) -> bytes:
    return value.encode("utf-16-be")


def decode_text(value: bytes) -> str:
    return value.decode("utf-16-be")
