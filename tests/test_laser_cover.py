"""[ASTRA_ENHANCEMENT_2026-11-21] Exercise cover selection during a laser warning."""
from types import SimpleNamespace
import unittest
from test_agent import recording
from agent.laser_cover import LaserCover
from agent.observation import Observer


class CoverTests(unittest.TestCase):
    def setUp(self):
        h, obs = recording()
        self.obs = obs[0]
        self.obs.update(t=10, mechs=[dict(id=5, kind='mech', pos=[-80,0,0],
                                          aim=[0,0], charging=True)])
        self.obs['self'].update(pos=[0,0,0], grounded=True, in_zone=True)
        self.obs['zone'].update(center=[0,0], radius=150, next_center=[0,0], next_radius=150)
        self.world = SimpleNamespace(ground=lambda *_: 0, walkable=lambda *_: True,
                                     clear=lambda start,end: end[1] < 5)
        self.cover = LaserCover(self.world, h['config'])

    def goal(self):
        return self.cover.goal(Observer().parse(self.obs))

    def test_find_shelter_and_release_when_charge_ends(self):
        self.assertAlmostEqual(self.goal()[1],6)
        self.obs['mechs'][0]['charging'] = False
        self.assertIsNone(self.goal())

    def test_blocked_route_or_exposed_head_disqualifies_shelter(self):
        self.world.walkable = lambda *_: False
        self.assertIsNone(self.goal())
        self.obs['t'] += .5
        self.world.walkable = lambda *_: True
        self.world.clear = lambda a,b: b[1] < 5 or b[2] > 8
        self.assertIsNone(self.goal())

    def test_zone_exit_and_unrelated_charge_do_not_divert(self):
        self.obs['self']['in_zone'] = False
        self.assertIsNone(self.goal())
        self.obs['self']['in_zone'] = True
        self.obs['mechs'][0]['aim'] = [3.14,0]
        self.assertIsNone(self.goal())
