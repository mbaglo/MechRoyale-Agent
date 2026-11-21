"""[CHATGPT_FIX_2026-11-21] Isolated V1 multi-threat escape regressions.

These tests inspect decisions, not official match outcomes. V1's other
components are intentionally unchanged.
"""
import math
from types import SimpleNamespace
import unittest

from agent.strategy import Strategy


def situation(enemies=None, urgent=False, next_radius=250):
    """Construct a minimal observation for V1's full Strategy.goal function."""
    return SimpleNamespace(
        me={"pos": [0., 0., 0.], "weapons": [None, None]},
        enemies=enemies or [],
        urgent=urgent,
        health=1.,
        obs={
            "zone": {
                "center": [0., 0.], "radius": 400.,
                "next_center": [0., 0.], "next_radius": next_radius
            },
            "cubes": [], "pickups": [], "drops": []
        }
    )


def enemy(identifier, x, y, vx=0, vy=0):
    """Create observed opponent positions and velocities without hidden state."""
    return {
        "id": identifier, "pos": [float(x), float(y), 0.],
        "vel": [float(vx), float(vy), 0.],
    }


class V1CrossfireTests(unittest.TestCase):
    def test_two_opposing_pursuers_escape_sideways(self):
        """[CHATGPT_FIX_2026-11-21] Avoid cancelling symmetric retreat vectors."""
        s = situation([
            enemy(1, 40, 0, -5, 0),
            enemy(2, -40, 0, 5, 0)
        ])
        goal = Strategy().goal(s, "conservative")
        self.assertGreater(math.dist(goal, [0., 0.]), 12.)
        self.assertGreater(abs(goal[1]), 8.)
        self.assertLess(math.dist(goal, [0., 0.]), 50.)

    def test_single_enemy_preserves_original_goal(self):
        """[CHATGPT_FIX_2026-11-21] A single enemy must not activate new logic."""
        s = situation([enemy(1, 40, 0)])
        self.assertEqual(Strategy().goal(s, "conservative"), [0., 0.])

    def test_balanced_mode_preserves_original_goal(self):
        """[CHATGPT_FIX_2026-11-21] Keep baseline behavior outside conservative."""
        s = situation([enemy(1, 40, 0), enemy(2, -40, 0)])
        self.assertEqual(Strategy().goal(s, "balanced"), [0., 0.])

    def test_zone_urgency_takes_priority(self):
        """[CHATGPT_FIX_2026-11-21] No detours during urgent zone travel."""
        s = situation([enemy(1, 40, 0), enemy(2, -40, 0)], urgent=True)
        self.assertEqual(Strategy().goal(s, "conservative"), [0., 0.])

    def test_tight_next_zone_prevents_unsafe_escape(self):
        """[CHATGPT_FIX_2026-11-21] Do not sacrifice zone safety to flee."""
        s = situation([enemy(1, 40, 0), enemy(2, -40, 0)], next_radius=20)
        self.assertEqual(Strategy().goal(s, "conservative"), [0., 0.])

    def test_safe_loot_target_preserved(self):
        """[CHATGPT_FIX_2026-11-21] Keep original loot decision when not swarmed."""
        s = situation([enemy(1, 190, 0)])
        s.obs["pickups"] = [{"id": 8001, "kind": "laser", "pos": [10., 0., 0.]}]
        self.assertEqual(Strategy().goal(s, "balanced"), [10., 0.])


if __name__ == "__main__":
    unittest.main()
