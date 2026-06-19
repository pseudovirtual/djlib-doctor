import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tests.support.fake_pyrekordbox_db import FakePyrekordboxDb
from tests.support.rekordbox_anlz_fixture import write_empty_cue_anlz_fixture
from tests.support.rekordbox_convert_fixture import write_operations
from tests.support.rekordbox_encrypted_assertions import (
    read_encrypted_library,
    read_encrypted_master_copy,
    rekordbox_not_running,
)
from tests.support.rekordbox_encrypted_fixture import (
    generate_encrypted_rekordbox_fixture,
    rekordbox_public_sqlcipher_key,
    requires_rekordbox_backend,
)

from djlib_doctor.rekordbox_anlz import read_anlz_beatgrid_times, read_anlz_cue_times
from djlib_doctor.rekordbox_convert import stage_rekordbox_conversion
from djlib_doctor.rekordbox_db_read import read_rekordbox_master_db
from djlib_doctor.rekordbox_db_write import update_track_location_and_cues


class RekordboxConvertDelayTests(unittest.TestCase):
    @requires_rekordbox_backend
    def test_auto_shift_uses_net_target_minus_source_decoder_delay(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Source.mp3"
            target = tmp / "Converted" / "Source.m4a"
            dat = tmp / "ANLZ0001.DAT"
            ext = tmp / "ANLZ0001.EXT"
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            source.write_bytes(b"synthetic mp3 bytes")
            write_empty_cue_anlz_fixture(dat, cue_tag=b"PCOB")
            write_empty_cue_anlz_fixture(ext, cue_tag=b"PCO2")
            ops = write_operations(tmp, source, target, dat, ext)

            def fake_encode(_source: Path, staged: Path, _preset: str) -> None:
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, staged)

            def fake_delay(path: Path) -> int:
                return 23 if path.name.endswith(".m4a") else 2

            with (
                patch("djlib_doctor.rekordbox_convert.require_audio_tools"),
                patch("djlib_doctor.rekordbox_convert.encode_audio", side_effect=fake_encode),
                patch("djlib_doctor.rekordbox_convert.encoder_delay_ms", side_effect=fake_delay),
                rekordbox_not_running(),
            ):
                stage = stage_rekordbox_conversion(fixture.encrypted_db, ops, tmp / "stage")

            operation = json.loads(stage.stage_manifest_path.read_text(encoding="utf-8"))["operations"][0]
            staged_library = read_encrypted_master_copy(stage.staged_db, tmp / "copied-net-delay-master.db")
            staged_dat = stage.stage_dir / "staged-anlz" / "OP-0001-ANLZ0001.DAT"
            staged_dat_cues = read_anlz_cue_times(staged_dat)
            staged_dat_grids = read_anlz_beatgrid_times(staged_dat)

        self.assertEqual(operation["source_decoder_delay_ms"], 2)
        self.assertEqual(operation["target_decoder_delay_ms"], 23)
        self.assertEqual(operation["measured_encoder_delay_ms"], 23)
        self.assertEqual(operation["cue_shift_ms"], 21)
        self.assertEqual(operation["anlz_files"][0]["shifted_cues"], 0)
        self.assertEqual(operation["anlz_files"][0]["shifted_beatgrid_entries"], 5)
        self.assertEqual(staged_library.tracks[0].path, target)
        self.assertAlmostEqual(staged_library.tracks[0].cues[0].start, 12.366, places=3)
        self.assertEqual(staged_dat_cues, ())
        self.assertEqual(staged_dat_grids[0].times_ms, (521, 1021, 1521))

    @requires_rekordbox_backend
    def test_conversion_stages_encrypted_master_db(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            source = tmp / "Source.wav"
            target = tmp / "Converted" / "Source.m4a"
            dat = tmp / "ANLZ0001.DAT"
            ext = tmp / "ANLZ0001.EXT"
            source.write_bytes(b"synthetic wav bytes")
            write_empty_cue_anlz_fixture(dat, cue_tag=b"PCOB")
            write_empty_cue_anlz_fixture(ext, cue_tag=b"PCO2")
            ops = write_operations(tmp, source, target, dat, ext)

            def fake_encode(_source: Path, staged: Path, _preset: str) -> None:
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, staged)

            with (
                patch("djlib_doctor.rekordbox_convert.require_audio_tools"),
                patch("djlib_doctor.rekordbox_convert.encode_audio", side_effect=fake_encode),
                patch("djlib_doctor.rekordbox_convert.encoder_delay_ms", return_value=21),
                rekordbox_not_running(),
            ):
                stage = stage_rekordbox_conversion(fixture.encrypted_db, ops, tmp / "stage")
                library = read_rekordbox_master_db(stage.staged_db, key=rekordbox_public_sqlcipher_key())

        self.assertEqual(library.tracks[0].path, target)
        self.assertEqual(library.tracks[0].cues[0].start, 12.345)

    @requires_rekordbox_backend
    def test_encrypted_write_persists_when_master_db_file_is_copied(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            copied = tmp / "copied-master.db"
            target = tmp / "Converted" / "Track One.m4a"

            with rekordbox_not_running():
                update_track_location_and_cues(fixture.encrypted_db, "1", target, 23, "test encrypted write")
                shutil.copy2(fixture.encrypted_db, copied)
                library = read_encrypted_library(copied)

        self.assertEqual(library.tracks[0].path, target)
        self.assertAlmostEqual(library.tracks[0].cues[0].start, 12.368, places=3)

    @requires_rekordbox_backend
    def test_write_refuses_missing_track_id(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Source.wav"
            target = tmp / "Converted" / "Source.m4a"
            db = tmp / "master.db"
            source.write_bytes(b"synthetic wav bytes")
            fixture = generate_encrypted_rekordbox_fixture(db)

            with self.assertRaisesRegex(RuntimeError, "matched 0 rows"):
                with rekordbox_not_running():
                    update_track_location_and_cues(fixture.encrypted_db, "999", target, 23, "test missing track")

    def test_conversion_uses_encrypted_opener_when_plain_sqlite_rejects_db(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            source = tmp / "Source.wav"
            target = tmp / "Converted" / "Source.m4a"
            dat = tmp / "ANLZ0001.DAT"
            ext = tmp / "ANLZ0001.EXT"
            fake_db = FakePyrekordboxDb()
            db.write_bytes(b"not a plain sqlite database")
            source.write_bytes(b"synthetic wav bytes")
            write_empty_cue_anlz_fixture(dat, cue_tag=b"PCOB")
            write_empty_cue_anlz_fixture(ext, cue_tag=b"PCO2")
            ops = write_operations(tmp, source, target, dat, ext)

            def fake_encode(_source: Path, staged: Path, _preset: str) -> None:
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, staged)

            with (
                patch("djlib_doctor.rekordbox_convert.require_audio_tools"),
                patch("djlib_doctor.rekordbox_convert.encode_audio", side_effect=fake_encode),
                patch("djlib_doctor.rekordbox_convert.encoder_delay_ms", return_value=0),
                patch("djlib_doctor.rekordbox_pyrekordbox.open_master_database", return_value=fake_db),
            ):
                stage = stage_rekordbox_conversion(db, ops, tmp / "stage")
            stage_exists = stage.stage_manifest_path.exists()

        self.assertTrue(stage_exists)
        self.assertTrue(fake_db.closed)
        self.assertTrue(fake_db.disposed)
        self.assertTrue(any("UPDATE" in statement and "djmdContent" in statement for statement in fake_db.statements))
        self.assertIn("PRAGMA wal_checkpoint(TRUNCATE)", fake_db.statements)


if __name__ == "__main__":
    unittest.main()
