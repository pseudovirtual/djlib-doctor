import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tests.support.rekordbox_anlz_fixture import write_empty_cue_anlz_fixture
from tests.support.rekordbox_convert_fixture import cue_row, make_rekordbox_db, write_operations

from djlib_doctor.rekordbox_anlz import read_anlz_beatgrid_times, read_anlz_cue_times
from djlib_doctor.rekordbox_convert import stage_rekordbox_conversion


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


if __name__ == "__main__":
    unittest.main()
