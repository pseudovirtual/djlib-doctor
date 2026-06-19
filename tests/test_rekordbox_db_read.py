from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from tests.support.rekordbox_encrypted_assertions import read_encrypted_library
from tests.support.rekordbox_encrypted_fixture import generate_encrypted_rekordbox_fixture, requires_rekordbox_backend

from djlib_doctor.cues import CueKind, CueType
from djlib_doctor.rekordbox_db_read import read_rekordbox_master_db
from djlib_doctor.rekordbox_pyrekordbox import PyrekordboxUnavailable


class RekordboxDbReadTests(unittest.TestCase):
    def test_reads_pyrekordbox_rows_into_native_library(self):
        db = _FakeRekordboxDb(
            contents=[
                SimpleNamespace(
                    ID="1",
                    FolderPath="/Music",
                    FileNameL="Track One.aiff",
                    Title="Track One",
                    ArtistName="Artist One",
                    AlbumName="Album",
                    GenreName="House",
                    KeyName="8A",
                    BPM=124.0,
                    Length=300000,
                    FileType=12,
                    Rating=3,
                    Commnt="Ready",
                )
            ],
            cues=[
                SimpleNamespace(
                    ContentID="1",
                    InMsec=12345,
                    OutMsec=56000,
                    Kind=2,
                    is_hot_cue=True,
                    is_memory_cue=False,
                    Comment="Loop B",
                )
            ],
            playlists=[SimpleNamespace(ID="10", Name="Fixture Playlist", Attribute=0, ParentID=None)],
            songs=[SimpleNamespace(PlaylistID="10", ContentID="1", TrackNo=1)],
        )

        library = read_rekordbox_master_db(Path("master.db"), opener=lambda *args, **kwargs: db)

        self.assertTrue(db.closed)
        self.assertEqual(len(library.tracks), 1)
        track = library.tracks[0]
        self.assertEqual(track.track_id, "1")
        self.assertEqual(track.name, "Track One")
        self.assertEqual(track.artist, "Artist One")
        self.assertEqual(track.path, Path("/Music/Track One.aiff"))
        self.assertEqual(track.format, "AIFF")
        self.assertEqual(track.bpm, 124.0)
        self.assertEqual(track.comments, "Ready")
        self.assertEqual(len(track.cues), 1)
        self.assertEqual(track.cues[0].kind, CueKind.HOTCUE)
        self.assertEqual(track.cues[0].cue_type, CueType.LOOP)
        self.assertEqual(track.cues[0].start, 12.345)
        self.assertEqual(track.cues[0].end, 56.0)
        self.assertEqual(track.cues[0].slot, 1)
        self.assertEqual(library.playlists[0].entries, ("1",))
        self.assertEqual(library.playlist_refs[0].playlist, "Fixture Playlist")

    def test_classifies_real_schema_cue_rows(self):
        db = _FakeRekordboxDb(
            contents=[
                SimpleNamespace(
                    ID="1",
                    FolderPath="/Music",
                    FileNameL="Track One.aiff",
                    Title="Track One",
                )
            ],
            cues=[
                SimpleNamespace(
                    ContentID="1", InMsec=1000, OutMsec=-1, Kind=0, is_hot_cue=False, is_memory_cue=True, Name="Memory"
                ),
                SimpleNamespace(
                    ContentID="1",
                    InMsec=2000,
                    OutMsec=-1,
                    Kind=3,
                    is_hot_cue=True,
                    is_memory_cue=False,
                    Name="Hotcue C",
                ),
                SimpleNamespace(
                    ContentID="1",
                    InMsec=3000,
                    OutMsec=4000,
                    Kind=0,
                    is_hot_cue=False,
                    is_memory_cue=True,
                    Name="Loop",
                ),
            ],
        )

        library = read_rekordbox_master_db(Path("master.db"), opener=lambda *args, **kwargs: db)
        memory, hotcue, loop = library.tracks[0].cues

        self.assertEqual(memory.kind, CueKind.MEMORY)
        self.assertEqual(memory.cue_type, CueType.CUE)
        self.assertIsNone(memory.slot)
        self.assertEqual(hotcue.kind, CueKind.HOTCUE)
        self.assertEqual(hotcue.cue_type, CueType.CUE)
        self.assertEqual(hotcue.slot, 2)
        self.assertEqual(loop.kind, CueKind.MEMORY)
        self.assertEqual(loop.cue_type, CueType.LOOP)
        self.assertEqual(loop.end, 4.0)

    @requires_rekordbox_backend
    def test_reads_generated_encrypted_fixture_when_backends_are_available(self):
        with TemporaryDirectory() as tmpdir:
            fixture = generate_encrypted_rekordbox_fixture(Path(tmpdir) / "master.db")
            library = read_encrypted_library(fixture.encrypted_db)

        self.assertEqual(library.tracks[0].track_id, "1")
        self.assertEqual(library.tracks[0].cues[0].start, 12.345)

    def test_read_wraps_query_time_database_driver_errors(self):
        db = _FakeRekordboxDb()
        db.contents = _FailingQuery()

        with self.assertRaisesRegex(PyrekordboxUnavailable, r"could not unlock or read Rekordbox master.db"):
            read_rekordbox_master_db(Path("master.db"), opener=lambda *args, **kwargs: db)

        self.assertTrue(db.closed)


class _FakeQuery(tuple):
    def all(self):
        return list(self)


class _FailingQuery:
    def all(self):
        raise sqlite3.DatabaseError("file is not a database")


class _FakeRekordboxDb:
    def __init__(self, contents=(), cues=(), playlists=(), songs=()):
        self.contents = _FakeQuery(contents)
        self.cues = _FakeQuery(cues)
        self.playlists = _FakeQuery(playlists)
        self.songs = _FakeQuery(songs)
        self.closed = False

    def get_content(self):
        return self.contents

    def get_cue(self):
        return self.cues

    def get_playlist(self):
        return self.playlists

    def get_playlist_songs(self):
        return self.songs

    def close(self):
        self.closed = True


if __name__ == "__main__":
    unittest.main()
