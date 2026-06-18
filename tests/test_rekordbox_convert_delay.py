import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tests.support.fake_pyrekordbox_db import FakePyrekordboxDb
from tests.support.rekordbox_anlz_fixture import write_empty_cue_anlz_fixture
from tests.support.rekordbox_convert_fixture import cue_row, make_rekordbox_db, write_operations
from tests.support.rekordbox_encrypted_fixture import (
    SqlcipherUnavailable,
    generate_encrypted_rekordbox_fixture,
    rekordbox_public_sqlcipher_key,
    skip_or_fail_for_missing_encrypted_backend,
)

from djlib_doctor.rekordbox_anlz import read_anlz_beatgrid_times, read_anlz_cue_times
from djlib_doctor.rekordbox_convert import stage_rekordbox_conversion
from djlib_doctor.rekordbox_db_read import read_rekordbox_master_db


class RekordboxConvertDelayTests(unittest.TestCase):
    def test_auto_shift_uses_net_target_minus_source_decoder_delay(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Source.mp3"
            target = tmp / "Converted" / "Source.m4a"
            db = tmp / "master.db"
            dat = tmp / "ANLZ0001.DAT"
            ext = tmp / "ANLZ0001.EXT"
            source.write_bytes(b"synthetic mp3 bytes")
            make_rekordbox_db(db, source)
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
            ):
                stage = stage_rekordbox_conversion(db, ops, tmp / "stage")

            operation = json.loads(stage.stage_manifest_path.read_text(encoding="utf-8"))["operations"][0]
            staged_db_row = cue_row(stage.staged_db)
            staged_dat = stage.stage_dir / "staged-anlz" / "OP-0001-ANLZ0001.DAT"
            staged_dat_cues = read_anlz_cue_times(staged_dat)
            staged_dat_grids = read_anlz_beatgrid_times(staged_dat)

        self.assertEqual(operation["source_decoder_delay_ms"], 2)
        self.assertEqual(operation["target_decoder_delay_ms"], 23)
        self.assertEqual(operation["measured_encoder_delay_ms"], 23)
        self.assertEqual(operation["cue_shift_ms"], 21)
        self.assertEqual(operation["anlz_files"][0]["shifted_cues"], 0)
        self.assertEqual(operation["anlz_files"][0]["shifted_beatgrid_entries"], 5)
        self.assertEqual(staged_db_row, (1021, 1521))
        self.assertEqual(staged_dat_cues, ())
        self.assertEqual(staged_dat_grids[0].times_ms, (521, 1021, 1521))

    def test_conversion_stages_encrypted_master_db(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            try:
                from pyrekordbox.db6 import database

                fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            except (ImportError, SqlcipherUnavailable) as exc:
                skip_or_fail_for_missing_encrypted_backend(self, exc)
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

            original_get_pid = database.get_rekordbox_pid
            database.get_rekordbox_pid = lambda: 0
            try:
                with (
                    patch("djlib_doctor.rekordbox_convert.require_audio_tools"),
                    patch("djlib_doctor.rekordbox_convert.encode_audio", side_effect=fake_encode),
                    patch("djlib_doctor.rekordbox_convert.encoder_delay_ms", return_value=21),
                ):
                    stage = stage_rekordbox_conversion(fixture.encrypted_db, ops, tmp / "stage")
                library = read_rekordbox_master_db(stage.staged_db, key=rekordbox_public_sqlcipher_key())
            finally:
                database.get_rekordbox_pid = original_get_pid

        self.assertEqual(library.tracks[0].path, target)
        self.assertEqual(library.tracks[0].cues[0].start, 12.345)

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
        self.assertTrue(any("UPDATE" in statement and "djmdContent" in statement for statement in fake_db.statements))


if __name__ == "__main__":
    unittest.main()
