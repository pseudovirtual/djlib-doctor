from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.compatibility import (
    AudioProbe,
    check_audio_compatibility,
    customize_audio_compatibility_profile,
    get_audio_compatibility_profile,
)
from djlib_doctor.plan import build_audio_compatibility_plan


PROBE_FIXTURE = Path(__file__).parent / "fixtures" / "audio" / "compatibility_probes.csv"


class CompatibilityTests(unittest.TestCase):
    def test_aac_m4a_passes_conservative_profile(self):
        result = check_audio_compatibility(
            AudioProbe(
                path="/fixture/music/aac-track.m4a",
                extension=".m4a",
                codec="aac",
                sample_rate_hz=44_100,
                bit_rate_kbps=256,
                duration_seconds=180.0,
            )
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.issues, ())

    def test_alac_m4a_fails_even_when_extension_is_allowed(self):
        result = check_audio_compatibility(
            AudioProbe(
                path="/fixture/music/alac-track.m4a",
                extension=".m4a",
                codec="alac",
                sample_rate_hz=44_100,
                bit_depth=16,
                duration_seconds=180.0,
            )
        )

        self.assertFalse(result.passed)
        self.assertEqual({issue.code for issue in result.issues}, {"unsupported_codec"})

    def test_broad_software_profile_allows_alac_and_flac(self):
        profile = get_audio_compatibility_profile("broad-software-library")

        alac = check_audio_compatibility(
            AudioProbe(
                path="/fixture/music/alac-track.m4a",
                extension=".m4a",
                codec="alac",
                sample_rate_hz=44_100,
                bit_depth=16,
            ),
            profile=profile,
        )
        flac = check_audio_compatibility(
            AudioProbe(
                path="/fixture/music/flac-track.flac",
                extension=".flac",
                codec="flac",
                sample_rate_hz=44_100,
                bit_depth=16,
            ),
            profile=profile,
        )

        self.assertTrue(alac.passed)
        self.assertTrue(flac.passed)

    def test_profile_overrides_can_require_wav_16(self):
        profile = customize_audio_compatibility_profile(
            get_audio_compatibility_profile("rekordbox-conservative"),
            allowed_extensions=("wav",),
            allowed_codecs=("pcm_s16le",),
            max_bit_depth=16,
        )

        aiff = check_audio_compatibility(
            AudioProbe(
                path="/fixture/music/aiff-track.aiff",
                extension=".aiff",
                codec="pcm_s24be",
                sample_rate_hz=44_100,
                bit_depth=24,
            ),
            profile=profile,
        )

        self.assertFalse(aiff.passed)
        self.assertEqual({issue.code for issue in aiff.issues}, {"unsupported_extension", "unsupported_codec", "bit_depth_too_high"})

    def test_audio_compatibility_plan_uses_probe_csv(self):
        report = build_audio_compatibility_plan(PROBE_FIXTURE)

        self.assertEqual(report.plan_type, "audio-compatibility")
        self.assertEqual(len(report.actions), 4)
        by_track = {action.track_id: action for action in report.actions}
        self.assertNotIn("1", by_track)
        self.assertIn("unsupported_codec", by_track["2"].evidence)
        self.assertIn("unsupported_extension", by_track["3"].evidence)
        self.assertIn("sample_rate_too_high", by_track["4"].evidence)
        self.assertIn("probe_failed", by_track["5"].evidence)

    def test_audio_compatibility_plan_cli_writes_plan(self):
        with TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "audio-compatibility.json"

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "plan",
                        "audio-compatibility",
                        "--probe-csv",
                        str(PROBE_FIXTURE),
                        "--out",
                        str(plan_path),
                    ]
                )

            data = json.loads(plan_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertIn("djlib-doctor plan: audio-compatibility", stdout.getvalue())
        self.assertEqual(data["summary"]["actions"], 4)

    def test_audio_compatibility_cli_lists_profiles_without_probe_csv(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["plan", "audio-compatibility", "--list-profiles"])

        self.assertEqual(exit_code, 0)
        self.assertIn("rekordbox-conservative", stdout.getvalue())
        self.assertIn("wav-16", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
