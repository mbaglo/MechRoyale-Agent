"""[ASTRA_ENHANCEMENT_2026-11-21] Measure discovery under the published yaw rate and field of view."""
import math
import unittest

from agent.combat import angle_delta
from agent.scan import QuietScan


def detection_times(coverage):
    bearings = [2*math.pi*i/24 for i in range(24)]
    latencies = []
    for initial in (0.,1.1,-2.2):
        found = {}
        scan = QuietScan(dict(fov_deg=120,memory_s=5))
        yaw = initial
        for tick in range(120):
            now = tick*.1
            for i,bearing in enumerate(bearings):
                if abs(angle_delta(bearing,yaw)) <= math.pi/3:
                    found.setdefault(i,now)
            if len(found) == len(bearings):
                break
            scan.observe(now,yaw,[])
            desired = scan.heading(now,yaw) if coverage else now*.6
            turn = max(-.4,min(.4,angle_delta(desired,yaw)))
            yaw = angle_delta(yaw+turn,0.)
        assert len(found) == len(bearings)
        latencies.extend(found.values())
    return latencies


class QuietScanTests(unittest.TestCase):
    def test_all_initial_bearings_covered_earlier(self):
        old,new = detection_times(False),detection_times(True)
        self.assertLess(max(new),max(old))
        self.assertLess(sum(new),sum(old))

    def test_only_actual_facing_marks_sectors_seen(self):
        scan = QuietScan(dict(fov_deg=120,memory_s=5))
        scan.observe(2,0,[])
        proposed = scan.heading(2,0)
        self.assertGreater(abs(proposed),math.pi/4)
        self.assertEqual(scan.seen[6],-math.inf)
        scan.observe(2.1,0,[{'id':3}])
        self.assertEqual(scan.last_contact,2.1)
        self.assertEqual(scan.seen[6],-math.inf)
