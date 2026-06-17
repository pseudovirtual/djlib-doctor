import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.library_model import rekordbox_xml_to_library
from djlib_doctor.rekordbox_xml import parse_rekordbox_xml


class LibraryModelTests(unittest.TestCase):
    def test_rekordbox_metadata_carries_into_core_library(self):
        with TemporaryDirectory() as tmpdir:
            xml = Path(tmpdir) / "metadata.xml"
            xml.write_text(
                """<?xml version="1.0" encoding="UTF-8"?>
<DJ_PLAYLISTS Version="1.0.0">
  <COLLECTION Entries="1">
    <TRACK TrackID="1" Name="Meta Track" Artist="Artist" AverageBpm="124.50" Tonality="8A" Colour="4" Rating="5" Comments="Fixture comment" Location="file://localhost/tmp/meta.aiff">
      <TEMPO Inizio="0.000" Bpm="124.50" Metro="4/4" Battito="1"/>
    </TRACK>
  </COLLECTION>
</DJ_PLAYLISTS>
""",
                encoding="utf-8",
            )

            track = rekordbox_xml_to_library(parse_rekordbox_xml(xml)).tracks[0]

        self.assertEqual(track.bpm, 124.5)
        self.assertEqual(track.key, "8A")
        self.assertEqual(track.color, "4")
        self.assertEqual(track.rating, 5)
        self.assertEqual(track.comments, "Fixture comment")
        self.assertEqual(track.beatgrid, ({"position": 0.0, "bpm": 124.5, "meter": "4/4", "beat": 1},))


if __name__ == "__main__":
    unittest.main()
