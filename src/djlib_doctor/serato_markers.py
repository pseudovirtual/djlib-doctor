from __future__ import annotations

import struct
from typing import Any

VERSION = (2, 1)
VERSION_FORMAT = ">2B"
CUE_COLORS = (b"\xcc\x00\x00", b"\xcc\x88\x00", b"\xcc\xcc\x00", b"\x00\xcc\x00", b"\x00\xcc\xcc", b"\x00\x00\xcc", b"\x88\x00\xcc", b"\xcc\x00\x88")


def build_markers2_payload(cue_intents: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> bytes:
    contents = [struct.pack(VERSION_FORMAT, *VERSION)]
    for intent in cue_intents:
        slot = int(intent.get("slot") or 0)
        label = str(intent.get("label") or "")
        if intent.get("intent") == "serato_hotcue":
            contents.append(_named_entry("CUE", _cue_entry(slot, int(intent["start_ms"]), label)))
        elif intent.get("intent") == "serato_saved_loop":
            contents.append(_named_entry("LOOP", _loop_entry(slot, int(intent["start_ms"]), int(intent.get("end_ms") or intent["start_ms"]), label)))
    return b"".join(contents)


def parse_markers2_payload(payload: bytes | None) -> tuple[dict[str, Any], ...]:
    if not payload or len(payload) < 2:
        return ()
    offset = 2
    markers = []
    while offset < len(payload):
        end = payload.find(b"\x00", offset)
        if end < 0 or end + 5 > len(payload):
            break
        name = payload[offset:end].decode("utf-8", errors="replace")
        length = struct.unpack(">I", payload[end + 1 : end + 5])[0]
        start = end + 5
        item = payload[start : start + length]
        if len(item) != length:
            break
        marker = _parse_marker(name, item)
        if marker:
            markers.append(marker)
        offset = start + length
    return tuple(markers)


def _parse_marker(name: str, payload: bytes) -> dict[str, Any] | None:
    if name == "CUE" and len(payload) >= 12:
        return {
            "kind": "hotcue",
            "cue_type": "cue",
            "start_ms": struct.unpack(">I", payload[2:6])[0],
            "end_ms": None,
            "slot": payload[1],
            "label": _label(payload[12:]),
        }
    if name == "LOOP" and len(payload) >= 22:
        return {
            "kind": "loop",
            "cue_type": "loop",
            "start_ms": struct.unpack(">I", payload[2:6])[0],
            "end_ms": struct.unpack(">I", payload[6:10])[0],
            "slot": payload[1],
            "label": _label(payload[22:]),
        }
    return None


def _cue_entry(index: int, position_ms: int, label: str) -> bytes:
    color = CUE_COLORS[index % len(CUE_COLORS)]
    return b"".join((struct.pack(">cBIc3s2s", b"\x00", index, position_ms, b"\x00", color, b"\x00\x00"), label[:51].encode("utf-8"), b"\x00"))


def _loop_entry(index: int, start_ms: int, end_ms: int, label: str) -> bytes:
    color = b"\xff" + CUE_COLORS[index % len(CUE_COLORS)]
    return b"".join((struct.pack(">cBII4s4s3s?", b"\x00", index, start_ms, end_ms, b"\x00\x00\x00\x00", color, b"\x00\x00\x00", False), label[:51].encode("utf-8"), b"\x00"))


def _named_entry(name: str, payload: bytes) -> bytes:
    return name.encode("utf-8") + b"\x00" + struct.pack(">I", len(payload)) + payload


def _label(payload: bytes) -> str:
    return payload.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
