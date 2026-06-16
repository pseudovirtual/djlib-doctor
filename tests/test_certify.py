from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.certify import certify_port_manifest
from djlib_doctor.cli import main
from djlib_doctor.io_utils import write_json


def _manifest() -> dict:
    return {
        "schema_version": "1.0",
        "mode": "dry_run_only",
        "source_platform": "rekordbox_xml",
        "target_platform": "serato",
        "scope": "playlist",
        "transfer_mode": "full",
        "target_crate_name": "RB - Set",
        "tracks": [{"serato_portable_id": "Music/a.mp3", "cue_intents": [{"slot": 1}], "unsupported": []}],
        "skipped": [],
        "warnings": [],
    }


class CertificationTests(unittest.TestCase):
    def test_certifies_healthy_serato_port_artifacts(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "port-manifest.json"
            write_json(manifest, _manifest())
            (root / "RB - Set.crate").write_text("crate", encoding="utf-8")
            (root / "unsupported.csv").write_text("track_id,artist,title,issue\n", encoding="utf-8")

            report = certify_port_manifest(manifest)

        self.assertTrue(report.passed)
        self.assertEqual(report.summary["tracks"], 1)
        self.assertEqual(report.summary["cues"], 1)

    def test_missing_preview_artifact_is_error(self):
        with TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "port-manifest.json"
            write_json(manifest, _manifest())

            report = certify_port_manifest(manifest)

        self.assertFalse(report.passed)
        self.assertEqual(report.issues[0].severity, "error")
        self.assertIn("missing", report.issues[0].message)

    def test_skipped_and_unsupported_rows_are_warnings(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            data = _manifest()
            data["tracks"][0]["unsupported"] = ["wav cue tags need validation"]
            data["skipped"] = [{"reason": "streaming"}]
            manifest = root / "port-manifest.json"
            write_json(manifest, data)
            (root / "RB - Set.crate").write_text("crate", encoding="utf-8")
            (root / "unsupported.csv").write_text("track_id,artist,title,issue\n", encoding="utf-8")

            report = certify_port_manifest(manifest)

        self.assertTrue(report.passed)
        self.assertEqual([issue.severity for issue in report.issues], ["warning", "warning"])

    def test_certify_cli_writes_json(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "port-manifest.json"
            out = root / "certification.json"
            write_json(manifest, _manifest())
            (root / "RB - Set.crate").write_text("crate", encoding="utf-8")
            (root / "unsupported.csv").write_text("track_id,artist,title,issue\n", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["certify", "port", "--port-manifest", str(manifest), "--out", str(out)])

            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(data["passed"])
        self.assertIn("Certification report written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
