from pathlib import Path
import json
import unittest

from djlib_doctor.serato_markers import encode_markers2_payload, parse_markers2_payload


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "serato_golden"


class SeratoMarkersGoldenVectorTests(unittest.TestCase):
    def test_parse_reference_hotcue_vector(self):
        fixture = _fixture("markers2-hotcue.json")

        self.assertEqual(
            parse_markers2_payload(bytes.fromhex(fixture["payload_hex"])),
            tuple(fixture["expected_markers"]),
        )

    def test_parse_reference_saved_loop_vector(self):
        fixture = _fixture("markers2-saved-loop.json")

        self.assertEqual(
            parse_markers2_payload(bytes.fromhex(fixture["payload_hex"])),
            tuple(fixture["expected_markers"]),
        )

    def test_decode_encode_decode_preserves_supported_golden_entries(self):
        payload = b"".join(bytes.fromhex(_fixture(path.name)["payload_hex"])[2:] for path in sorted(FIXTURE_DIR.glob("markers2-*.json")))
        payload = b"\x01\x01" + payload

        decoded = parse_markers2_payload(payload)

        self.assertEqual(parse_markers2_payload(encode_markers2_payload(decoded)), decoded)


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
