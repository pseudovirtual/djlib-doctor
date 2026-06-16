from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import sqlite3
import unittest

from djlib_doctor.certify import certify_port_manifest
from djlib_doctor.cli import main
from djlib_doctor.io_utils import write_json
from djlib_doctor.serato_crate import write_serato_crate
from tests.helpers import make_serato_root


def _rb_to_serato_manifest() -> dict:
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


def _serato_to_rb_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "mode": "dry_run_only",
        "source_platform": "serato",
        "target_platform": "rekordbox_xml",
        "scope": "crate",
        "transfer_mode": "full",
        "tracks": [{"track_id": "1", "path": "/Music/a.aiff", "cues": [{"slot": 1}], "unsupported": []}],
        "skipped": [],
    }


class CertificationTests(unittest.TestCase):
    def test_certifies_healthy_serato_port_artifacts(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "port-manifest.json"
            write_json(manifest, _rb_to_serato_manifest())
            (root / "RB - Set.crate").write_text("crate", encoding="utf-8")
            (root / "unsupported.csv").write_text("track_id,artist,title,issue\n", encoding="utf-8")

            report = certify_port_manifest(manifest)

        self.assertTrue(report.passed)
        self.assertEqual(report.summary["tracks"], 1)
        self.assertEqual(report.summary["cues"], 1)

    def test_missing_preview_artifact_is_error(self):
        with TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "port-manifest.json"
            write_json(manifest, _rb_to_serato_manifest())

            report = certify_port_manifest(manifest)

        self.assertFalse(report.passed)
        self.assertEqual(report.issues[0].severity, "error")
        self.assertIn("missing", report.issues[0].message)

    def test_skipped_and_unsupported_rows_are_warnings(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            data = _rb_to_serato_manifest()
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
            write_json(manifest, _rb_to_serato_manifest())
            (root / "RB - Set.crate").write_text("crate", encoding="utf-8")
            (root / "unsupported.csv").write_text("track_id,artist,title,issue\n", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["certify", "port", "--port-manifest", str(manifest), "--out", str(out)])

            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(data["passed"])
        self.assertIn("Certification report written:", stdout.getvalue())

    def test_serato_to_rekordbox_certification_notes_staged_db_when_present(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "port-manifest.json"
            write_json(manifest, _serato_to_rb_manifest())
            (root / "rekordbox-preview.xml").write_text("<DJ_PLAYLISTS />", encoding="utf-8")
            stage = root / "rekordbox-stage"
            stage.mkdir()
            (stage / "rekordbox-db-stage-manifest.json").write_text("{}", encoding="utf-8")

            report = certify_port_manifest(manifest)

        self.assertTrue(report.passed)
        self.assertIn("rekordbox.stage", [issue.code for issue in report.issues])

    def test_direction_specific_certify_alias_uses_same_core(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "port-manifest.json"
            write_json(manifest, _serato_to_rb_manifest())
            (root / "rekordbox-preview.xml").write_text("<DJ_PLAYLISTS />", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["certify", "serato-to-rb", "--port-manifest", str(manifest), "--json"])

        data = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(data["target_platform"], "rekordbox_xml")

    def test_certifies_generated_rekordbox_to_serato_preview(self):
        fixture = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"
        with TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "rb"
            main(
                [
                    "port",
                    "rb-to-serato",
                    "--rekordbox-xml",
                    str(fixture),
                    "--playlist",
                    "ROOT / Fixture Playlist",
                    "--out",
                    str(out),
                ]
            )

            report = certify_port_manifest(out / "port-manifest.json")

        self.assertTrue(report.passed)
        self.assertEqual(report.target_platform, "serato")

    def test_certifies_generated_serato_to_rekordbox_preview(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            library = root / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            conn = sqlite3.connect(library / "root.sqlite")
            try:
                conn.execute(
                    "INSERT INTO asset(revision, portable_id, file_name, name, artist) VALUES(?, ?, ?, ?, ?)",
                    (1, "Music/Track One.aiff", "Track One.aiff", "Track One", "Artist One"),
                )
                conn.commit()
            finally:
                conn.close()
            crate = root / "Test.crate"
            write_serato_crate(crate, ("Music/Track One.aiff",))
            out = root / "srb"
            main(
                [
                    "port",
                    "serato-to-rb",
                    "--serato-library-dir",
                    str(library),
                    "--crate",
                    str(crate),
                    "--collection-root",
                    "/Music",
                    "--out",
                    str(out),
                ]
            )

            report = certify_port_manifest(out / "port-manifest.json")

        self.assertTrue(report.passed)
        self.assertEqual(report.target_platform, "rekordbox_xml")


if __name__ == "__main__":
    unittest.main()
