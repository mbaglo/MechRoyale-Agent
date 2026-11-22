"""[CHATGPT_ENHANCEMENT_2026-11-21] Charging laser hitscan lane regression tests."""
import copy
import math
import unittest
from types import SimpleNamespace

from test_agent import recording
from agent.observation import Observer
from agent.navigation import Navigator


class ChargingLaserLaneTests(unittest.TestCase):
    def setUp(self):
        _, frames = recording()
        self.obs = copy.deepcopy(frames[0])
        self.obs.update(t=10., events=[], sounds=[], projectiles=[], drops=[],
                        crates=[], cubes=[], pickups=[])
        self.obs['self'].update(pos=[0.,0.,0.], vel=[0.,0.,0.], grounded=True,
                                hp=1400, energy=100, in_zone=True)
        self.obs['zone'].update(center=[0.,0.], radius=300,
                                next_center=[0.,0.], next_radius=250,
                                shrink_end=500)
        self.enemy = dict(id=5, kind='mech', pos=[100.,0.,0.],
                          vel=[0.,0.,0.], aim=[math.pi,0.], cubes=0,
                          hp=1400, weapons=['gun','laser'], charging=True)
        self.obs['mechs'] = [self.enemy]
        self.world = SimpleNamespace(walkable=lambda *_: True, clear=lambda *_: True)

    def action(self, urgent=None):
        situation = Observer().parse(self.obs)
        if urgent is not None:
            situation.urgent = urgent
        return Navigator(self.world).move(situation, [80.,0.], 'balanced')[0]

    def test_exposed_charging_laser_forces_side_step(self):
        step = self.action()
        self.assertGreater(abs(step[1]), .5)
        self.assertLess(step[0], 1.)

    def test_noncharging_laser_keeps_prior_goal(self):
        self.enemy['charging'] = False
        self.assertGreater(self.action()[0], .9)

    def test_aiming_elsewhere_is_not_a_threat(self):
        self.enemy['aim'] = [math.pi/2,0.]
        self.assertGreater(self.action()[0], .9)

    def test_cover_blocks_laser_lane_reaction(self):
        self.world.clear = lambda *_: False
        self.assertGreater(self.action()[0], .9)

    def test_distant_charger_is_not_a_threat(self):
        self.enemy['pos'] = [350.,0.,0.]
        self.assertGreater(self.action()[0], .9)

    def test_urgent_zone_and_airborne_routes_are_preserved(self):
        self.assertGreater(self.action(urgent=True)[0], .9)
        self.obs['self']['grounded'] = False
        self.assertGreater(self.action()[0], .9)

    def test_unwalkable_lateral_candidates_are_rejected(self):
        self.world.walkable = lambda start,end,stats: abs(end[1]) < 1.
        step = self.action()
        self.assertLess(abs(step[1]), .2)


if __name__ == '__main__':
    unittest.main()
