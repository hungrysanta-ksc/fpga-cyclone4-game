"""Small contract checks for endpoint log completeness and epoch ordering."""

import unittest

from analyze_endpoint_backlog import analyze


GOOD = """
# STALL_PROFILE frame=0 start_cycle=0 end_cycle=9
# FRAME_DATA_PASS frame=0 cycles=9
# STALL_PROFILE frame=1 start_cycle=10 end_cycle=19
# FRAME_DATA_PASS frame=1 cycles=9
# STALL_PROFILE frame=2 start_cycle=20 end_cycle=29
# FRAME_DATA_PASS frame=2 cycles=9
# HOST_EVENT kind=6 bus_cycle=20 epoch=0 installs=1
# HOST_EVENT kind=7 bus_cycle=21 epoch=0 installs=1
# HOST_EVENT kind=6 bus_cycle=30 epoch=1 installs=2
# HOST_EVENT kind=7 bus_cycle=31 epoch=1 installs=2
# HOST_EVENT kind=6 bus_cycle=40 epoch=1 installs=3
# HOST_EVENT kind=7 bus_cycle=41 epoch=1 installs=3
# HOST_EVENT kind=6 bus_cycle=50 epoch=2 installs=4
# ENDPOINT_PASS commits=3 published=3
# HOST_PASS installs=4 consumed=2
# DIAGNOSTIC_ONLY deadline_misses=0
"""


class EndpointBacklogTest(unittest.TestCase):
    def test_repeat_without_missing_source_epoch(self):
        report = analyze(GOOD, 10, 1.0, 1.0)
        self.assertEqual(report["repeat_epochs"], [1])
        self.assertEqual(report["frames"], 3)
        self.assertEqual(report["first_visible_from_pipeline_start_ms"]["observed_epochs"], 2)

    def test_missing_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze(GOOD.replace("# FRAME_DATA_PASS frame=1 cycles=9\n", ""), 10, 1.0, 1.0)

    def test_skipped_epoch_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze(GOOD.replace("bus_cycle=30 epoch=1", "bus_cycle=30 epoch=2"), 10, 1.0, 1.0)

    def test_deadline_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze(GOOD.replace("deadline_misses=0", "deadline_misses=1"), 10, 1.0, 1.0)


if __name__ == "__main__":
    unittest.main()
