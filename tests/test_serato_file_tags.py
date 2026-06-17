import base64
import unittest
from pathlib import Path

from djlib_doctor.serato_file_tags import (
    decode_serato_geob_payload,
    read_serato_file_tags,
    read_serato_markers2_file_tags,
)

INNER_MARKERS2 = bytes.fromhex("01 01 43 55 45 00 00 00 00 12 00 02 00 00 56 ce 00 cc cc 00 00 00 43 75 65 20 43 00")
INNER_BEATGRID = bytes.fromhex("01 00 00 00 00 02 00 00 00 00 00 00 00 40 41 f0 00 00 43 00 00 00 00")


class FakeFrame:
    def __init__(self, data: bytes):
        self.data = data


class FakeAudio:
    def __init__(self, tags: dict[str, object]):
        self.tags = tags


class SeratoFileTagTests(unittest.TestCase):
    def test_decode_geob_payload_unwraps_serato_base64(self):
        wrapped = b"\x01\x01" + b"\n".join(_chunks(base64.b64encode(INNER_MARKERS2).rstrip(b"="), 12)) + b"\x00"

        self.assertEqual(decode_serato_geob_payload(wrapped), INNER_MARKERS2)

    def test_read_markers2_from_geob_frame(self):
        wrapped = b"\x01\x01" + base64.b64encode(INNER_MARKERS2).rstrip(b"=") + b"\x00"

        markers = read_serato_markers2_file_tags(
            Path("track.aiff"),
            file_loader=lambda path: FakeAudio({"GEOB:Serato Markers2": FakeFrame(wrapped)}),
        )

        self.assertEqual(markers[0]["label"], "Cue C")
        self.assertEqual(markers[0]["color"], "cccc00")

    def test_read_markers2_and_beatgrid_from_geob_frames(self):
        markers = _wrap(INNER_MARKERS2)
        beatgrid = _wrap(INNER_BEATGRID)

        tags = read_serato_file_tags(
            Path("track.aiff"),
            file_loader=lambda path: FakeAudio(
                {
                    "GEOB:Serato Markers2": FakeFrame(markers),
                    "GEOB:Serato BeatGrid": FakeFrame(beatgrid),
                }
            ),
        )

        self.assertEqual(tags["markers2"][0]["label"], "Cue C")
        self.assertEqual(
            tags["beatgrid"],
            (
                {"kind": "beatgrid_marker", "position": 0.0, "beats_till_next_marker": 64},
                {"kind": "beatgrid_terminal", "position": 30.0, "bpm": 128.0},
                {"kind": "beatgrid_footer", "unknown": 0},
            ),
        )


def _chunks(data: bytes, size: int) -> list[bytes]:
    return [data[index : index + size] for index in range(0, len(data), size)]


def _wrap(data: bytes) -> bytes:
    return b"\x01\x01" + b"\n".join(_chunks(base64.b64encode(data).rstrip(b"="), 72)) + b"\x00"


if __name__ == "__main__":
    unittest.main()
