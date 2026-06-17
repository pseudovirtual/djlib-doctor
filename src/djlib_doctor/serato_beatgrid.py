from __future__ import annotations

import struct
from typing import Any

VERSION = b"\x01\x00"


def parse_beatgrid_payload(payload: bytes | None) -> tuple[dict[str, Any], ...]:
    if not payload or len(payload) < 7 or not payload.startswith(VERSION):
        return ()
    count = struct.unpack(">I", payload[2:6])[0]
    offset = 6
    markers = []
    for index in range(count):
        if offset + 8 > len(payload):
            return tuple(markers)
        position = struct.unpack(">f", payload[offset : offset + 4])[0]
        data = payload[offset + 4 : offset + 8]
        if index == count - 1:
            markers.append({"kind": "beatgrid_terminal", "position": position, "bpm": struct.unpack(">f", data)[0]})
        else:
            markers.append({"kind": "beatgrid_marker", "position": position, "beats_till_next_marker": struct.unpack(">I", data)[0]})
        offset += 8
    if offset < len(payload):
        markers.append({"kind": "beatgrid_footer", "unknown": payload[offset]})
    return tuple(markers)
