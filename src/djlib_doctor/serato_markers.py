from __future__ import annotations

import base64
import struct
from typing import Any

VERSION = (1, 1)
VERSION_FORMAT = ">2B"
VERSION_BYTES = struct.pack(VERSION_FORMAT, *VERSION)
GEOB_MIN_BYTES = 470
GEOB_WRAP_BYTES = 72
LOOP_PREFIX = b"\x00\x00\x00\xff"
TRACK_COLOR_WHITE = b"\xff\xff\xff"
CUE_COLORS = (
    b"\xcc\x00\x00",
    b"\xcc\x88\x00",
    b"\xcc\xcc\x00",
    b"\x00\xcc\x00",
    b"\x00\xcc\xcc",
    b"\x00\x00\xcc",
    b"\x88\x00\xcc",
    b"\xcc\x00\x88",
)


def build_markers2_payload(cue_intents: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> bytes:
    markers = []
    for intent in cue_intents:
        if intent.get("intent") == "serato_hotcue":
            markers.append(_marker(intent, "hotcue", "cue"))
        elif intent.get("intent") == "serato_saved_loop":
            markers.append(_marker(intent, "loop", "loop"))
    return encode_markers2_payload(tuple(markers))


def encode_markers2_payload(markers: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> bytes:
    contents = [VERSION_BYTES, _named_entry("COLOR", b"\x00" + TRACK_COLOR_WHITE), _named_entry("BPMLOCK", b"\x00")]
    for marker in markers:
        slot = int(marker.get("slot") or 0)
        label = str(marker.get("label") or "")
        if marker.get("cue_type") == "loop":
            contents.append(
                _named_entry(
                    "LOOP",
                    _loop_entry(
                        slot,
                        int(marker["start_ms"]),
                        int(marker.get("end_ms") or marker["start_ms"]),
                        label,
                        str(marker.get("color") or ""),
                    ),
                )
            )
        else:
            contents.append(
                _named_entry("CUE", _cue_entry(slot, int(marker["start_ms"]), label, str(marker.get("color") or "")))
            )
    contents.append(b"\x00")
    return b"".join(contents)


def encode_markers2_geob_data(entry_stream: bytes) -> bytes:
    encoded = base64.b64encode(entry_stream)
    wrapped = b"\n".join(encoded[index : index + GEOB_WRAP_BYTES] for index in range(0, len(encoded), GEOB_WRAP_BYTES))
    return (VERSION_BYTES + wrapped).ljust(GEOB_MIN_BYTES, b"\x00")


def _marker(intent: dict[str, Any], kind: str, cue_type: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "cue_type": cue_type,
        "start_ms": int(intent["start_ms"]),
        "end_ms": None if cue_type == "cue" else int(intent.get("end_ms") or intent["start_ms"]),
        "slot": int(intent.get("slot") or 0),
        "label": str(intent.get("label") or ""),
        "color": str(intent.get("color") or ""),
    }


def parse_markers2_payload(payload: bytes | None) -> tuple[dict[str, Any], ...]:
    if not payload or len(payload) < 2:
        return ()
    offset = 2
    markers = []
    while offset < len(payload):
        if payload[offset] == 0:
            break
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
            "color": payload[7:10].hex(),
        }
    if name == "LOOP" and len(payload) >= 20:
        return {
            "kind": "loop",
            "cue_type": "loop",
            "start_ms": struct.unpack(">I", payload[2:6])[0],
            "end_ms": struct.unpack(">I", payload[6:10])[0],
            "slot": payload[1],
            "label": _label(payload[20:]),
            "color": payload[18:19].hex(),
        }
    return None


def _cue_entry(index: int, position_ms: int, label: str, color_hex: str = "") -> bytes:
    color = _cue_color(index, color_hex)
    return b"".join(
        (
            struct.pack(">cBIc3s2s", b"\x00", index, position_ms, b"\x00", color, b"\x00\x00"),
            label[:51].encode("utf-8"),
            b"\x00",
        )
    )


def _loop_entry(index: int, start_ms: int, end_ms: int, label: str, color_hex: str = "") -> bytes:
    color = _loop_color(index, color_hex)
    return b"".join(
        (
            struct.pack(
                ">cBII4s4sB?", b"\x00", index, start_ms, end_ms, b"\x00\x00\x00\x00", LOOP_PREFIX, color, False
            ),
            label[:51].encode("utf-8"),
            b"\x00",
        )
    )


def _named_entry(name: str, payload: bytes) -> bytes:
    return name.encode("utf-8") + b"\x00" + struct.pack(">I", len(payload)) + payload


def _label(payload: bytes) -> str:
    return payload.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def _cue_color(index: int, color_hex: str) -> bytes:
    if len(color_hex) == 6:
        return bytes.fromhex(color_hex)
    return CUE_COLORS[index % len(CUE_COLORS)]


def _loop_color(index: int, color_hex: str) -> int:
    if len(color_hex) >= 2:
        return int(color_hex[:2], 16)
    return CUE_COLORS[index % len(CUE_COLORS)][0]
