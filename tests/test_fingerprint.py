from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.fingerprint import compare_files, fingerprint_file, scan_fingerprints


class FingerprintTests(unittest.TestCase):
    def test_identical_files_classify_as_exact_duplicate(self):
        with TemporaryDirectory() as tmpdir:
            left = Path(tmpdir) / "left.wav"
            right = Path(tmpdir) / "right.wav"
            left.write_bytes(bytes(range(64)) * 4)
            right.write_bytes(left.read_bytes())

            result = compare_files(left, right)

        self.assertEqual(result.classification, "exact_duplicate")
        self.assertEqual(result.byte_similarity, 1.0)

    def test_nearby_content_classifies_as_byte_similar(self):
        with TemporaryDirectory() as tmpdir:
            left = Path(tmpdir) / "left.aiff"
            right = Path(tmpdir) / "right.aiff"
            left.write_bytes(bytes(range(128)) * 8)
            right.write_bytes(bytes(range(1, 129)) * 8)

            result = compare_files(left, right)

        self.assertEqual(result.classification, "byte_similar")
        self.assertGreater(result.byte_similarity, 0.88)

    def test_different_encodings_are_not_claimed_as_same_audio(self):
        with TemporaryDirectory() as tmpdir:
            pcm_payload = bytes(range(64)) * 4
            wav = Path(tmpdir) / "track.wav"
            aiff = Path(tmpdir) / "track.aiff"
            wav.write_bytes(b"RIFF-WAVE" + pcm_payload)
            aiff.write_bytes(b"FORM-AIFF" + pcm_payload)

            result = compare_files(wav, aiff)
            data = result.to_dict()

        self.assertEqual(result.classification, "byte_similar")
        self.assertNotIn("same", result.classification)
        self.assertEqual(data["comparison_basis"], "raw_file_bytes")
        self.assertFalse(data["claims_audio_identity"])

    def test_unrelated_content_classifies_as_different(self):
        with TemporaryDirectory() as tmpdir:
            left = Path(tmpdir) / "left.mp3"
            right = Path(tmpdir) / "right.mp3"
            left.write_bytes(b"\x00" * 1024)
            right.write_bytes(b"\xff" * 1024)

            result = compare_files(left, right)

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
        self.assertIn("Byte fingerprint report written:", stdout.getvalue())
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
        self.assertEqual(data["classification"], "exact_duplicate")

    def test_missing_file_returns_input_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = main(["fingerprint", "file", "/no/such/track.wav"])

        self.assertEqual(exit_code, 3)
        self.assertIn("djlib-doctor fingerprint: ERROR", stderr.getvalue())

    def test_scan_fingerprints_only_audio_files_in_stable_order(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "b.wav").write_bytes(b"bbb")
            (root / "a.txt").write_text("not audio", encoding="utf-8")
            nested = root / "Nested"
            nested.mkdir()
            (nested / "a.mp3").write_bytes(b"aaa")

            manifest = scan_fingerprints(root)

        self.assertEqual(manifest.root, str(root))
        self.assertEqual([Path(item.path).name for item in manifest.files], ["a.mp3", "b.wav"])

    def test_scan_cli_redacts_paths(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            secret = root / "Private Artist - Secret Track.aiff"
            secret.write_bytes(b"secret")
            out = root / "fingerprints.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["fingerprint", "scan", str(root), "--out", str(out), "--redact-paths"])

            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(data["redacted_paths"])
        self.assertEqual(data["files"][0]["path"], "<redacted>/track-000001.aiff")
        self.assertNotIn("Secret", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
