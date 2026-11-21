"""[CHATGPT_FIX_2026-11-21] Crossfire escape regression tests."""
import math
import unittest
from types import SimpleNamespace

from agent.strategy import Strategy


class CrossfireEscapeTests(unittest.TestCase):
    def situation(self, enemies, *, urgent=False, routes=None, zone_radius=250):
        """Build a minimal observation-backed Situation without match simulation."""
        if routes is None:
            routes = ((1., 0.), (-1., 0.), (0., 1.), (0., -1.))
        return SimpleNamespace(
            obs={
                'zone': {
                    'center': [0., 0.], 'radius': 350.,
                    'next_center': [0., 0.], 'next_radius': zone_radius
                },
                'cubes': [], 'pickups': [], 'drops': [],
            },
            me={'pos': [0., 0., 0.], 'weapons': [None, None]},
            enemies=enemies,
            health=.75,
            urgent=urgent,
            emergency=True,
            pressure=3.,
            crossfire=1.,
            pursuing=2,
            escape_routes=routes,
            threat_weights={enemy['id']: 1. for enemy in enemies},
            phase='mid',
        )

    def test_opposing_pursuers_do_not_cancel_into_stationary_goal(self):
        """[CHATGPT_FIX_2026-11-21] Symmetric east/west pursuit must escape north/south."""
        enemies = [
            {'id': 1, 'pos': [40., 0., 0.], 'vel': [-5., 0., 0.]},
            {'id': 2, 'pos': [-40., 0., 0.], 'vel': [5., 0., 0.]},
        ]
        s = self.situation(enemies)
        goal = Strategy().goal(s, 'conservative')
        self.assertGreater(math.dist(goal, s.me['pos'][:2]), 10)
        self.assertGreater(abs(goal[1]), 10)
        self.assertLess(math.dist(goal, [0, 0]), 230)

    def test_no_escape_routes_preserves_fallback(self):
        """[CHATGPT_FIX_2026-11-21] Keep original fallback when geometry blocks all sectors."""
        enemies = [
            {'id': 1, 'pos': [40., 0., 0.], 'vel': [-5., 0., 0.]},
            {'id': 2, 'pos': [-40., 0., 0.], 'vel': [5., 0., 0.]},
        ]
        s = self.situation(enemies, routes=())
        self.assertEqual(Strategy().goal(s, 'conservative'), [0., 0.])

    def test_escape_sector_never_moves_farther_outside_next_zone(self):
        """[CHATGPT_FIX_2026-11-21] Escape must not sacrifice shrinking-zone safety."""
        enemies = [
            {'id': 1, 'pos': [40., 0., 0.], 'vel': [-5., 0., 0.]},
            {'id': 2, 'pos': [-40., 0., 0.], 'vel': [5., 0., 0.]},
        ]
        s = self.situation(enemies, routes=((1., 0.), (0., 1.)), zone_radius=10)
        s.me['pos'] = [12., 0., 0.]
        goal = Strategy().goal(s, 'conservative')
        self.assertLessEqual(math.dist(goal, [0., 0.]), 12.000001)


if __name__ == '__main__':
    unittest.main()
