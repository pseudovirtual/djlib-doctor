from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.fingerprint import compare_tracks, fingerprint_file


class FingerprintTests(unittest.TestCase):
    def test_identical_files_classify_as_same(self):
        with TemporaryDirectory() as tmpdir:
            left = Path(tmpdir) / "left.wav"
            right = Path(tmpdir) / "right.wav"
            left.write_bytes(bytes(range(64)) * 4)
            right.write_bytes(left.read_bytes())

            result = compare_tracks(left, right)

        self.assertEqual(result.classification, "same")
        self.assertEqual(result.similarity, 1.0)

    def test_nearby_content_classifies_as_similar(self):
        with TemporaryDirectory() as tmpdir:
            left = Path(tmpdir) / "left.aiff"
            right = Path(tmpdir) / "right.aiff"
            left.write_bytes(bytes(range(128)) * 8)
            right.write_bytes(bytes(range(1, 129)) * 8)

            result = compare_tracks(left, right)

        self.assertEqual(result.classification, "similar")
        self.assertGreater(result.similarity, 0.88)

    def test_unrelated_content_classifies_as_different(self):
        with TemporaryDirectory() as tmpdir:
            left = Path(tmpdir) / "left.mp3"
            right = Path(tmpdir) / "right.mp3"
            left.write_bytes(b"\x00" * 1024)
            right.write_bytes(b"\xff" * 1024)

            result = compare_tracks(left, right)

        self.assertEqual(result.classification, "different")

    def test_file_cli_writes_fingerprint_report(self):
        with TemporaryDirectory() as tmpdir:
            track = Path(tmpdir) / "track.wav"
            out = Path(tmpdir) / "fingerprint.json"
            track.write_bytes(b"abc123" * 16)
            expected_sha = fingerprint_file(track).sha256
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["fingerprint", "file", str(track), "--out", str(out)])

            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertIn("Fingerprint report written:", stdout.getvalue())
        self.assertEqual(data["sha256"], expected_sha)

    def test_compare_cli_prints_json(self):
        with TemporaryDirectory() as tmpdir:
            left = Path(tmpdir) / "left.wav"
            right = Path(tmpdir) / "right.wav"
            left.write_bytes(b"same")
            right.write_bytes(b"same")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["fingerprint", "compare", str(left), str(right)])

        data = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(data["classification"], "same")

    def test_missing_file_returns_input_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = main(["fingerprint", "file", "/no/such/track.wav"])

        self.assertEqual(exit_code, 3)
        self.assertIn("djlib-doctor fingerprint: ERROR", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
