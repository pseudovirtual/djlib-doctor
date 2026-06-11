from pathlib import Path
import unittest

from djlib_doctor.cues import CueKind, CueType
from djlib_doctor.locations import LocationKind, parse_location
from djlib_doctor.rekordbox_xml import parse_rekordbox_xml


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class RekordboxXmlTests(unittest.TestCase):
    def test_collection_tracks_are_separate_from_playlist_refs(self):
        library = parse_rekordbox_xml(FIXTURE)

        self.assertEqual(len(library.tracks), 3)
        self.assertEqual(len(library.playlist_refs), 2)
        self.assertEqual(len(library.playlists), 1)
        self.assertEqual(library.playlists[0].entries, ("1", "3"))
        self.assertEqual(library.playlist_refs[0].playlist, "ROOT / Fixture Playlist")

    def test_streaming_placeholder_is_not_a_local_file(self):
        library = parse_rekordbox_xml(FIXTURE)
        streaming = library.track_by_id()["3"]

        self.assertIs(streaming.location_kind, LocationKind.STREAMING_PLACEHOLDER)
        self.assertIsNone(streaming.path)

    def test_local_path_with_streaming_word_is_still_local(self):
        kind, path = parse_location("file://localhost/Users/example/Music/SoundCloud%20Downloads/track.aiff")

        self.assertIs(kind, LocationKind.LOCAL_FILE)
        self.assertEqual(str(path), "/Users/example/Music/SoundCloud Downloads/track.aiff")

    def test_file_url_preserves_encoded_fragment_characters(self):
        kind, path = parse_location("file:///Users/example/Music/Track%20%231%3F.aiff")

        self.assertIs(kind, LocationKind.LOCAL_FILE)
        self.assertEqual(str(path), "/Users/example/Music/Track #1?.aiff")

    def test_cues_decode_memory_hotcue_and_loop(self):
        library = parse_rekordbox_xml(FIXTURE)
        cues = library.track_by_id()["1"].cues

        self.assertIs(cues[0].kind, CueKind.MEMORY)
        self.assertIsNone(cues[0].slot)
        self.assertIs(cues[1].kind, CueKind.HOTCUE)
        self.assertEqual(cues[1].slot, 0)
        self.assertEqual(cues[1].hotcue_label, "A")
        self.assertIs(cues[2].cue_type, CueType.LOOP)
        self.assertEqual(cues[2].start, 48.0)
        self.assertEqual(cues[2].end, 56.0)


if __name__ == "__main__":
    unittest.main()
