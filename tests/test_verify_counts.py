import unittest
from pathlib import Path

from djlib_doctor.rekordbox_xml import parse_rekordbox_xml
from djlib_doctor.verify import verify_library

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"
VALIDATION_FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "validation_issues.xml"


class VerifyCountsTests(unittest.TestCase):
    def test_verify_counts_distinguish_collection_refs_and_placeholders(self):
        report = verify_library(parse_rekordbox_xml(FIXTURE))

        self.assertEqual(report.collection_tracks, 3)
        self.assertEqual(report.playlist_refs, 2)
        self.assertEqual(report.local_file_tracks, 2)
        self.assertEqual(report.streaming_placeholders, 1)
        self.assertEqual(report.unknown_location_tracks, 0)
        self.assertEqual(len(report.missing_local_files), 2)

    def test_no_file_check_allows_fixture_to_pass_without_real_music(self):
        report = verify_library(parse_rekordbox_xml(FIXTURE), check_files=False)

        self.assertTrue(report.passed)
        self.assertEqual(report.missing_local_files, ())
        self.assertEqual(report.cue_count, 3)
        self.assertEqual(report.hotcue_count, 2)
        self.assertEqual(report.memory_cue_count, 1)
        self.assertEqual(report.loop_count, 1)

    def test_validation_findings_capture_failures_and_warnings(self):
        report = verify_library(parse_rekordbox_xml(VALIDATION_FIXTURE), check_files=False)

        self.assertFalse(report.passed)
        self.assertEqual(
            {finding.code for finding in report.failures}, {"duplicate_track_id", "missing_playlist_track"}
        )
        self.assertEqual({finding.code for finding in report.warnings}, {"unknown_location", "unknown_cue_type"})

    def test_json_report_has_stable_shape(self):
        report = verify_library(
            parse_rekordbox_xml(VALIDATION_FIXTURE), check_files=False, source_path=str(VALIDATION_FIXTURE)
        )
        data = report.to_dict()

        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["status"], "fail")
        self.assertEqual(data["source"]["path"], str(VALIDATION_FIXTURE))
        self.assertFalse(data["source"]["check_files"])
        self.assertEqual(data["counts"]["failures"], 2)
        self.assertEqual(data["counts"]["warnings"], 2)
        self.assertEqual(data["failures"][0]["severity"], "failure")
        self.assertGreaterEqual(len(data["next_actions"]), 1)


if __name__ == "__main__":
    unittest.main()
