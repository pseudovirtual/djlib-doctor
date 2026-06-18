import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.helpers import insert_serato_asset, make_rekordbox_import_db, make_serato_root

from djlib_doctor.cli import main
from djlib_doctor.serato_crate import write_serato_crate

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class PortScopeMatrixTests(unittest.TestCase):
    def test_rekordbox_to_serato_scopes_stage_library_artifacts(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            music = tmp / "_Serato_"
            library.mkdir()
            music.mkdir()
            make_serato_root(library / "root.sqlite")

            for scope, scope_args in _rekordbox_scopes():
                out = tmp / f"rb-{scope}"
                exit_code = main(
                    [
                        "migrate",
                        "rb-to-serato",
                        "--rekordbox-xml",
                        str(FIXTURE),
                        *scope_args,
                        "--out",
                        str(out),
                        "--stage-library",
                        "--serato-library-dir",
                        str(library),
                        "--serato-music-dir",
                        str(music),
                    ]
                )
                manifest = json.loads((out / "port" / "port-manifest.json").read_text(encoding="utf-8"))

                self.assertEqual(exit_code, 0)
                self.assertEqual(manifest["scope"], scope)
                self.assertTrue((out / "serato-stage" / "serato-stage-manifest.json").exists())

    def test_serato_to_rekordbox_scopes_stage_db_imports(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            insert_serato_asset(library / "root.sqlite", "Music/Track One.aiff")
            crate = tmp / "Test.crate"
            write_serato_crate(crate, ("Music/Track One.aiff",))
            db = tmp / "master.db"
            make_rekordbox_import_db(db)

            for scope, scope_args in _serato_scopes(crate):
                out = tmp / f"serato-{scope}"
                exit_code = main(
                    [
                        "migrate",
                        "serato-to-rb",
                        "--serato-library-dir",
                        str(library),
                        *scope_args,
                        "--collection-root",
                        str(tmp),
                        "--out",
                        str(out),
                        "--stage-db",
                        "--rekordbox-db",
                        str(db),
                    ]
                )
                manifest = json.loads((out / "port" / "port-manifest.json").read_text(encoding="utf-8"))

                self.assertEqual(exit_code, 0)
                self.assertEqual(manifest["scope"], scope)
                self.assertTrue((out / "rekordbox-stage" / "rekordbox-db-stage-manifest.json").exists())


def _rekordbox_scopes() -> tuple[tuple[str, list[str]], ...]:
    return (
        ("playlist", ["--playlist", "ROOT / Fixture Playlist"]),
        ("track", ["--track-id", "1"]),
        ("collection", ["--collection"]),
    )


def _serato_scopes(crate: Path) -> tuple[tuple[str, list[str]], ...]:
    return (
        ("crate", ["--crate", str(crate)]),
        ("track", ["--portable-id", "Music/Track One.aiff"]),
        ("collection", ["--collection"]),
    )


if __name__ == "__main__":
    unittest.main()
