import os
import unittest
from pathlib import Path

from djlib_doctor.serato_file_tags import read_serato_file_tags

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REAL_SERATO_DIR = ROOT / "tests" / "fixtures" / "real" / "serato" / "audio-tags"
AUDIO_SUFFIXES = {".aif", ".aiff", ".flac", ".m4a", ".mp3"}
MAX_POSITION_MS = 24 * 60 * 60 * 1000


class RealSeratoMarkers2Tests(unittest.TestCase):
    def test_configured_real_serato_files_parse_markers2_positions(self):
        files = _real_serato_files()
        if not files:
            self.skipTest("Set DJLIB_DOCTOR_REAL_SERATO or add local files under tests/fixtures/real/serato/audio-tags")

        parsed_markers = 0
        for path in files:
            tags = read_serato_file_tags(path)
            for marker in tags["markers2"]:
                if marker.get("kind") not in {"hotcue", "loop"}:
                    continue
                parsed_markers += 1
                self.assertGreaterEqual(int(marker["start_ms"]), 0, str(path))
                self.assertLess(int(marker["start_ms"]), MAX_POSITION_MS, str(path))
                end_ms = marker.get("end_ms")
                if end_ms is not None:
                    self.assertGreaterEqual(int(end_ms), int(marker["start_ms"]), str(path))
                    self.assertLess(int(end_ms), MAX_POSITION_MS, str(path))
        self.assertGreater(parsed_markers, 0, "Configured real Serato files did not contain parsed Markers2 cues")


def _real_serato_files() -> tuple[Path, ...]:
    configured = os.environ.get("DJLIB_DOCTOR_REAL_SERATO", "")
    roots = [Path(item).expanduser() for item in configured.split(os.pathsep) if item]
    if not roots:
        roots = [DEFAULT_REAL_SERATO_DIR]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(path for path in root.rglob("*") if path.suffix.lower() in AUDIO_SUFFIXES)
    return tuple(sorted(files))


if __name__ == "__main__":
    unittest.main()
