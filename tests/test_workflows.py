from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from djlib_doctor.serato_crate import write_serato_crate
from djlib_doctor.workflows import migrate_rekordbox_to_serato, migrate_serato_to_rekordbox


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


def make_serato_root(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE serato(revision INT DEFAULT 0);
            INSERT INTO serato(revision) VALUES(10);
            CREATE TABLE asset(id INTEGER PRIMARY KEY AUTOINCREMENT, revision INTEGER NOT NULL, portable_id TEXT NOT NULL DEFAULT '', file_name TEXT, file_size INTEGER, type TEXT DEFAULT '', format TEXT DEFAULT '', artist TEXT DEFAULT '', comments TEXT DEFAULT '', name TEXT DEFAULT '', album TEXT DEFAULT '', genre TEXT DEFAULT '', key TEXT DEFAULT '', bpm REAL, length_ms INTEGER, time_added INTEGER DEFAULT 0, time_modified INTEGER DEFAULT 0, analysis_flags INTEGER DEFAULT 0, architectures INTEGER DEFAULT 0);
            CREATE UNIQUE INDEX asset__unique_portable_id ON asset(portable_id COLLATE NOCASE);
            CREATE TABLE space_asset(id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL, space_id INTEGER NOT NULL, UNIQUE(asset_id, space_id));
            CREATE TABLE container(id INTEGER PRIMARY KEY AUTOINCREMENT, revision INTEGER NOT NULL, parent_id INTEGER, name TEXT NOT NULL, type INTEGER DEFAULT 1, list_order INTEGER NOT NULL, space_id INTEGER DEFAULT NULL, time_added INTEGER DEFAULT 0, expanded INTEGER DEFAULT 0, portable_id TEXT DEFAULT '', UNIQUE(parent_id, name COLLATE NOCASE, type));
            INSERT INTO container(id, revision, parent_id, name, type, list_order, space_id, time_added, portable_id)
            VALUES(3, 10, 0, 'Serato Library root', 0, 1, 2, 1, '');
            CREATE TABLE container_asset(id INTEGER PRIMARY KEY AUTOINCREMENT, revision INTEGER NOT NULL, container_id INTEGER NOT NULL, space_asset_id INTEGER NOT NULL, list_order INTEGER, time_added INTEGER DEFAULT 0);
            """
        )
        conn.commit()
    finally:
        conn.close()


class WorkflowTests(unittest.TestCase):
    def test_migrate_rekordbox_to_serato_can_plan_and_stage(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            music = tmp / "_Serato_"
            library.mkdir()
            music.mkdir()
            make_serato_root(library / "root.sqlite")

            result = migrate_rekordbox_to_serato(
                rekordbox_xml=FIXTURE,
                playlist="ROOT / Fixture Playlist",
                out_dir=tmp / "run",
                serato_library_dir=library,
                serato_music_dir=music,
                stage_library=True,
                stage_tags=True,
            )

        self.assertTrue(result.port_manifest.name.endswith(".json"))
        self.assertIsNotNone(result.serato_stage)
        self.assertIsNotNone(result.tag_stage)

    def test_migrate_serato_to_rekordbox_writes_preview(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            crate = tmp / "Test.crate"
            write_serato_crate(crate, ("Music/Track One.aiff",))

            result = migrate_serato_to_rekordbox(
                serato_library_dir=library,
                crate=crate,
                collection_root=Path("/Users/test"),
                out_dir=tmp / "run",
            )

        self.assertTrue(result.port_manifest.name.endswith(".json"))
        self.assertTrue(result.rekordbox_xml_preview.name.endswith(".xml"))


if __name__ == "__main__":
    unittest.main()
