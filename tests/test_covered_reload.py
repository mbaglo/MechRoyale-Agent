"""[ASTRA_ENHANCEMENT_2026-11-21] Verify reload timing using observed kit poses."""
import unittest
from test_agent import recording
from agent.policy import Bot


class CoveredReloadTests(unittest.TestCase):
    def test_reload_request_leaves_time_before_recorded_lane_reopens(self):
        hello, frames = recording()
        bot = Bot(hello)
        requests = []
        for frame in frames:
            action = bot.act(frame)
            if 19.7 <= frame['t'] <= 24.1 and action['reload']:
                self.assertTrue(frame['mechs'])
                self.assertFalse(any(action['fire']))
                requests.append(frame['t'])
        self.assertTrue(requests)
        duration = hello['config']['weapons']['gun']['reload']
        self.assertLess(requests[0] + duration, 24.1)
