import contextlib
import io
import json
import math
import shutil
import sqlite3
import struct
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.support.rekordbox_anlz_fixture import write_anlz_fixture

from djlib_doctor.cli import main
from djlib_doctor.rekordbox_anlz import read_anlz_beatgrid_times, read_anlz_cue_times


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg and ffprobe are required")
class RekordboxConvertTests(unittest.TestCase):
    def test_real_m4a_encode_compensates_db_and_anlz_cues(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Track One.wav"
            target = tmp / "Converted" / "Track One.m4a"
            db = tmp / "master.db"
            dat = tmp / "ANLZ0001.DAT"
            ext = tmp / "ANLZ0001.EXT"
            _write_click_wav(source)
            _make_rekordbox_db(db, source)
            write_anlz_fixture(dat, cue_tag=b"PCOB", time_ms=1000, loop_ms=1500)
            write_anlz_fixture(ext, cue_tag=b"PCO2", time_ms=1000, loop_ms=1500)
            ops = _write_operations(tmp, source, target, dat, ext)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "stage",
                        "rekordbox-convert",
                        "--db",
                        str(db),
                        "--operations",
                        str(ops),
                        "--stage-dir",
                        str(tmp / "stage"),
                    ]
                )
            manifest = json.loads((tmp / "stage" / "rekordbox-convert-stage-manifest.json").read_text(encoding="utf-8"))
            shift_ms = manifest["operations"][0]["cue_shift_ms"]
            staged_db_row = _cue_row(tmp / "stage" / "master.db")
            staged_dat = read_anlz_cue_times(tmp / "stage" / "staged-anlz" / "OP-0001-ANLZ0001.DAT")[0]
            staged_ext = read_anlz_cue_times(tmp / "stage" / "staged-anlz" / "OP-0001-ANLZ0001.EXT")[0]
            staged_dat_grids = read_anlz_beatgrid_times(tmp / "stage" / "staged-anlz" / "OP-0001-ANLZ0001.DAT")
            staged_ext_grids = read_anlz_beatgrid_times(tmp / "stage" / "staged-anlz" / "OP-0001-ANLZ0001.EXT")
            token = manifest["install_token"]

            with contextlib.redirect_stdout(io.StringIO()):
                install_exit = main(
                    [
                        "install",
                        "rekordbox-convert",
                        "--stage-dir",
                        str(tmp / "stage"),
                        "--db",
                        str(db),
                        "--confirm-token",
                        token,
                        "--skip-process-check",
                    ]
                )
            target_exists = target.exists()

        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox conversion stage written:", stdout.getvalue())
        self.assertGreater(shift_ms, 0)
        self.assertEqual(manifest["operations"][0]["cue_shift"], "auto")
        self.assertEqual(manifest["operations"][0]["measured_encoder_delay_ms"], shift_ms)
        self.assertEqual(staged_db_row, (1000 + shift_ms, 1500 + shift_ms))
        self.assertEqual(staged_dat.time_ms, 1000 + shift_ms)
        self.assertEqual(staged_dat.loop_time_ms, 1500 + shift_ms)
        self.assertEqual(staged_ext.time_ms, 1000 + shift_ms)
        self.assertEqual(staged_ext.loop_time_ms, 1500 + shift_ms)
        self.assertEqual(staged_dat_grids[0].times_ms, (500 + shift_ms, 1000 + shift_ms, 1500 + shift_ms))
        self.assertEqual(staged_dat_grids[1].times_ms, (250 + shift_ms, 750 + shift_ms))
        self.assertEqual(staged_ext_grids[0].times_ms, (500 + shift_ms, 1000 + shift_ms, 1500 + shift_ms))
        self.assertEqual(staged_ext_grids[1].times_ms, (250 + shift_ms, 750 + shift_ms))
        self.assertEqual(install_exit, 0)
        self.assertTrue(target_exists)

    def test_cue_shift_none_records_measurement_without_moving_positions(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Track One.wav"
            target = tmp / "Converted" / "Track One.m4a"
            db = tmp / "master.db"
            dat = tmp / "ANLZ0001.DAT"
            ext = tmp / "ANLZ0001.EXT"
            _write_click_wav(source)
            _make_rekordbox_db(db, source)
            write_anlz_fixture(dat, cue_tag=b"PCOB", time_ms=1000, loop_ms=1500)
            write_anlz_fixture(ext, cue_tag=b"PCO2", time_ms=1000, loop_ms=1500)
            ops = _write_operations(tmp, source, target, dat, ext)

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "stage",
                        "rekordbox-convert",
                        "--db",
                        str(db),
                        "--operations",
                        str(ops),
                        "--stage-dir",
                        str(tmp / "stage"),
                        "--cue-shift",
                        "none",
                    ]
                )
            manifest = json.loads((tmp / "stage" / "rekordbox-convert-stage-manifest.json").read_text(encoding="utf-8"))
            operation = manifest["operations"][0]
            staged_db_row = _cue_row(tmp / "stage" / "master.db")
            staged_dat = read_anlz_cue_times(tmp / "stage" / "staged-anlz" / "OP-0001-ANLZ0001.DAT")[0]
            staged_dat_grids = read_anlz_beatgrid_times(tmp / "stage" / "staged-anlz" / "OP-0001-ANLZ0001.DAT")

        self.assertEqual(exit_code, 0)
        self.assertEqual(operation["cue_shift"], "none")
        self.assertGreater(operation["measured_encoder_delay_ms"], 0)
        self.assertEqual(operation["cue_shift_ms"], 0)
        self.assertEqual(staged_db_row, (1000, 1500))
        self.assertEqual(staged_dat.time_ms, 1000)
        self.assertEqual(staged_dat.loop_time_ms, 1500)
        self.assertEqual(staged_dat_grids[0].times_ms, (500, 1000, 1500))


def _write_click_wav(path: Path) -> None:
    sample_rate = 44100
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = []
        for index in range(sample_rate * 2):
            value = 0
            if sample_rate <= index < sample_rate + 400:
                value = int(28000 * math.sin(2 * math.pi * 1000 * (index - sample_rate) / sample_rate))
            frames.append(struct.pack("<h", value))
        handle.writeframes(b"".join(frames))


def _make_rekordbox_db(path: Path, audio: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE djmdContent(ID INTEGER PRIMARY KEY, FolderPath TEXT, FileNameL TEXT, Title TEXT);
            CREATE TABLE djmdCue(ID INTEGER PRIMARY KEY, ContentID INTEGER, InMsec INTEGER, OutMsec INTEGER);
            """
        )
        conn.execute(
            "INSERT INTO djmdContent(ID, FolderPath, FileNameL, Title) VALUES(1, ?, ?, 'Track One')",
            (str(audio.parent), audio.name),
        )
        conn.execute("INSERT INTO djmdCue(ID, ContentID, InMsec, OutMsec) VALUES(1, 1, 1000, 1500)")
        conn.commit()
    finally:
        conn.close()


def _cue_row(path: Path) -> tuple[int, int]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT InMsec, OutMsec FROM djmdCue WHERE ID = 1").fetchone()
    finally:
        conn.close()


def _write_operations(tmp: Path, source: Path, target: Path, dat: Path, ext: Path) -> Path:
    ops = tmp / "convert.json"
    ops.write_text(
        json.dumps(
            {
                "operations": [
                    {
                        "track_id": "1",
                        "source": str(source),
                        "target": str(target),
                        "preset": "aac-m4a-128",
                        "anlz_files": [str(dat), str(ext)],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return ops
