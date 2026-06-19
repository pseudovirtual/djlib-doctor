import unittest

from djlib_doctor.port_cue_models import PortCueTiming
from djlib_doctor.port_rekordbox_serato import SeratoCueIntent
from djlib_doctor.port_serato_rekordbox import RekordboxPortCue


class PortCueModelTests(unittest.TestCase):
    def test_directional_cues_share_timing_value_object(self):
        timing = PortCueTiming(start_ms=1234, end_ms=5678, slot=2, label="Break").to_dict()

        serato = SeratoCueIntent("serato_saved_loop", 1234, 5678, 2, "Break", "hotcue", "loop").to_dict()
        rekordbox = RekordboxPortCue("hotcue", "loop", 1234, 5678, 2, "Break", "#ff0000").to_dict()

        for key, value in timing.items():
            self.assertEqual(serato[key], value)
            self.assertEqual(rekordbox[key], value)
        self.assertEqual(serato["intent"], "serato_saved_loop")
        self.assertEqual(rekordbox["kind"], "hotcue")


if __name__ == "__main__":
    unittest.main()
