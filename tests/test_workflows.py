import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.serato_crate import write_serato_crate
from djlib_doctor.workflows import migrate_rekordbox_to_serato, migrate_serato_to_rekordbox
from helpers import make_serato_root

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


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
