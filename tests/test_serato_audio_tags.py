from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest
from unittest import mock

from djlib_doctor.cli import main
from djlib_doctor.port_rekordbox_serato import build_rekordbox_to_serato_plan, write_rekordbox_to_serato_plan
from djlib_doctor.serato_audio_tags import (
    build_markers2_payload,
    build_serato_audio_tag_stage,
    install_serato_audio_tag_stage,
)


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class SeratoAudioTagsTests(unittest.TestCase):
    def test_build_markers2_payload_contains_cue_and_loop_entries(self):
        plan = build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist")
        payload = build_markers2_payload(plan.tracks[0].to_dict()["cue_intents"])

        self.assertIn(b"CUE\x00", payload)
        self.assertIn(b"LOOP\x00", payload)

    def test_stage_audio_tags_records_unsupported_when_dependency_or_file_missing(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            outputs = write_rekordbox_to_serato_plan(
                build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist"),
                tmp / "port",
            )

            report = build_serato_audio_tag_stage(Path(outputs["manifest"]), tmp / "tag-stage")
            data = json.loads(report.stage_manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["summary"]["tracks"], 1)
        self.assertEqual(data["summary"]["tagged_copies"], 0)
        self.assertEqual(data["tracks"][0]["status"], "source_missing")
        self.assertTrue(data["install_token"].startswith("INSTALL_SERATO_TAGS:"))

    def test_install_audio_tag_stage_requires_confirmation_token(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            outputs = write_rekordbox_to_serato_plan(
                build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist"),
                tmp / "port",
            )
            report = build_serato_audio_tag_stage(Path(outputs["manifest"]), tmp / "tag-stage")

            with self.assertRaises(ValueError):
                install_serato_audio_tag_stage(tmp / "tag-stage", confirm_token="wrong")

    def test_install_audio_tag_stage_refuses_when_source_changed_after_stage(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "track.aiff"
            source.write_bytes(b"audio")
            manifest = tmp / "port-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "tracks": [
                            {
                                "source_id": "1",
                                "artist": "Artist",
                                "title": "Title",
                                "path": str(source),
                                "cue_intents": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch("djlib_doctor.serato_audio_tags._write_tags", side_effect=lambda path, track: path.write_bytes(b"tagged")):
                report = build_serato_audio_tag_stage(manifest, tmp / "tag-stage")
            source.write_bytes(b"changed")

            with self.assertRaises(RuntimeError):
                install_serato_audio_tag_stage(tmp / "tag-stage", confirm_token=report.install_token)

    def test_audio_tag_stage_cli_writes_manifest(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            outputs = write_rekordbox_to_serato_plan(
                build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist"),
                tmp / "port",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "stage",
                        "serato-tags",
                        "--port-manifest",
                        str(outputs["manifest"]),
                        "--stage-dir",
                        str(tmp / "tag-stage"),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Serato audio tag stage written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
