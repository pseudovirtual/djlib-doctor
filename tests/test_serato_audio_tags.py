import base64
import contextlib
import io
import json
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from djlib_doctor.cli import main
from djlib_doctor.port_rekordbox_serato import build_rekordbox_to_serato_plan, write_rekordbox_to_serato_plan
from djlib_doctor.serato_audio_tags import build_serato_audio_tag_stage, install_serato_audio_tag_stage
from djlib_doctor.serato_markers import build_markers2_payload

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"
GOLDEN = Path(__file__).parent / "fixtures" / "serato_golden"


class SeratoAudioTagsTests(unittest.TestCase):
    def test_build_markers2_payload_contains_cue_and_loop_entries(self):
        plan = build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist")
        payload = build_markers2_payload(plan.tracks[0].to_dict()["cue_intents"])

        self.assertIn(b"CUE\x00", payload)
        self.assertIn(b"LOOP\x00", payload)

    def test_write_tags_uses_real_serato_markers2_geob_container_for_all_formats(self):
        fixture = json.loads((GOLDEN / "geob-markers2-real-hotcue.json").read_text(encoding="utf-8"))
        expected_stream = bytes.fromhex(fixture["entry_stream_hex"])
        expected_body = fixture["base64_body"].encode("ascii")
        track = {
            "title": "Title",
            "cue_intents": [{"intent": "serato_hotcue", "slot": 2, "start_ms": 22222, "label": "Cue C"}],
        }

        with TemporaryDirectory() as tmpdir, _fake_mutagen() as written:
            for filename in ("track.aiff", "track.mp3", "track.m4a"):
                from djlib_doctor.serato_audio_tags import _write_tags

                _write_tags(Path(tmpdir) / filename, track)

        for payload in written:
            self.assertEqual(payload[:2], b"\x01\x01")
            self.assertNotEqual(payload[2:6], b"CUE\x00")
            self.assertEqual(len(payload), 470)
            body = payload[2:].split(b"\x00", 1)[0]
            self.assertEqual(body, expected_body)
            self.assertEqual(base64.b64decode(body.replace(b"\n", b"")), expected_stream)

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
            build_serato_audio_tag_stage(Path(outputs["manifest"]), tmp / "tag-stage")

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
            with mock.patch(
                "djlib_doctor.serato_audio_tags._write_tags",
                side_effect=lambda path, track: path.write_bytes(b"tagged"),
            ):
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


class _FakeTags(dict):
    def setall(self, key, values):
        self[key] = values


class _FakeAudio:
    def __init__(self, path):
        self.path = path
        self.tags = _FakeTags()

    def add_tags(self):
        self.tags = _FakeTags()

    def save(self):
        pass


class _FakeGEOB:
    def __init__(self, **kwargs):
        self.data = kwargs["data"]


class _FakeMP4FreeForm(bytes):
    def __new__(cls, data, dataformat=None):
        return bytes.__new__(cls, data)


@contextlib.contextmanager
def _fake_mutagen():
    written = []

    def audio_factory(path):
        audio = _FakeAudio(path)
        instances.append(audio)
        return audio

    def geob_factory(**kwargs):
        frame = _FakeGEOB(**kwargs)
        written.append(frame.data)
        return frame

    def freeform_factory(data, dataformat=None):
        written.append(bytes(data))
        return _FakeMP4FreeForm(data, dataformat=dataformat)

    instances = []
    aiff = types.ModuleType("mutagen.aiff")
    aiff.AIFF = audio_factory
    mp3 = types.ModuleType("mutagen.mp3")
    mp3.MP3 = audio_factory
    mp4 = types.ModuleType("mutagen.mp4")
    mp4.MP4 = audio_factory
    mp4.MP4FreeForm = freeform_factory
    mp4.AtomDataType = types.SimpleNamespace(IMPLICIT=0)
    id3 = types.ModuleType("mutagen.id3")
    id3.GEOB = geob_factory
    for name in ("TALB", "TBPM", "TCON", "TIT2", "TKEY", "TPE1"):
        setattr(id3, name, lambda **kwargs: kwargs)
    with mock.patch.dict(
        sys.modules,
        {"mutagen.aiff": aiff, "mutagen.id3": id3, "mutagen.mp3": mp3, "mutagen.mp4": mp4},
    ):
        yield written


if __name__ == "__main__":
    unittest.main()
