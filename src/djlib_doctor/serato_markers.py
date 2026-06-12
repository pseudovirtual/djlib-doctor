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


def _cue_entry(index: int, position_ms: int, label: str) -> bytes:
    color = CUE_COLORS[index % len(CUE_COLORS)]
    return b"".join((struct.pack(">cBIc3s2s", b"\x00", index, position_ms, b"\x00", color, b"\x00\x00"), label[:51].encode("utf-8"), b"\x00"))


def _loop_entry(index: int, start_ms: int, end_ms: int, label: str) -> bytes:
    color = b"\xff" + CUE_COLORS[index % len(CUE_COLORS)]
    return b"".join((struct.pack(">cBII4s4s3s?", b"\x00", index, start_ms, end_ms, b"\x00\x00\x00\x00", color, b"\x00\x00\x00", False), label[:51].encode("utf-8"), b"\x00"))


def _named_entry(name: str, payload: bytes) -> bytes:
    return name.encode("utf-8") + b"\x00" + struct.pack(">I", len(payload)) + payload
