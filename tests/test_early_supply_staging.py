"""[CHATGPT_ENHANCEMENT_2026-11-21] Safe announced-drop routing regression tests.

Tests use official recorded observation/config fields but synthetic resource
placement. They verify decisions, not the official score or match outcomes.
"""
import copy
import unittest

from test_agent import recording
from agent.drop_approach import stage_supply_goal
from agent.observation import Observer
from agent.strategy import Strategy


class WalkableWorld:
    """[CHATGPT_ENHANCEMENT_2026-11-21] Bounded ground-path test double."""

    def __init__(self, can_walk=True):
        self.can_walk = can_walk
        self.calls = 0

    def walkable(self, start, end, stats):
        self.calls += 1
        return self.can_walk


class EarlySupplyStagingTests(unittest.TestCase):
    """[CHATGPT_ENHANCEMENT_2026-11-21] Conserve existing goals and limit exposure."""

    def setUp(self):
        hello, frames = recording()
        self.obs = copy.deepcopy(frames[0])
        self.obs.update(t=75., tick=1500, mechs=[], events=[], sounds=[],
                        cubes=[], projectiles=[], pickups=[], drops=[], crates=[])
        me = self.obs['self']
        me.update(pos=[0., 0., 0.], vel=[0., 0., 0.],
                  hp=me['max_hp'], grounded=True, in_zone=True, energy=100.)
        self.obs['zone'] = dict(center=[0., 0.], radius=560.,
                                next_center=[0., 0.], next_radius=380.,
                                shrink_start=100., shrink_end=175., dps=20.)
        self.obs['drops'] = [dict(id=20000, pos=[145., 0., 0.],
                                  lands_in=17., radius=8., capture_s=4.,
                                  progress=0., holder=None)]
        self.world = WalkableWorld()

    def choose(self, mode='balanced'):
        state = Observer().parse(self.obs)
        baseline = Strategy().goal(state, mode)
        staged = stage_supply_goal(state, baseline, mode, self.world)
        return baseline, staged

    def test_preposition_before_original_eight_second_window(self):
        baseline, staged = self.choose()
        self.assertEqual(baseline, [0., 0.])
        self.assertEqual(staged, [145., 0.])
        self.assertEqual(self.world.calls, 1)

    def test_preserves_visible_cube_and_weapon_goals(self):
        self.obs['cubes'] = [dict(id=5000, pos=[20., 0., 0.])]
        baseline, staged = self.choose()
        self.assertEqual(staged, baseline)
        self.assertEqual(staged, [20., 0.])
        self.assertEqual(self.world.calls, 0)
        self.obs['cubes'] = []
        self.obs['pickups'] = [dict(id=8001, kind='laser', pos=[30., 0., 0.])]
        baseline, staged = self.choose()
        self.assertEqual(staged, baseline)
        self.assertEqual(staged, [30., 0.])

    def test_does_not_rush_when_not_enough_time(self):
        self.obs['drops'][0]['lands_in'] = 7.
        self.assertEqual(self.choose()[1], [0., 0.])

    def test_does_not_wait_before_announcement_or_after_landing(self):
        for remaining in (23., 0., -1.):
            with self.subTest(remaining=remaining):
                self.obs['drops'][0]['lands_in'] = remaining
                self.assertEqual(self.choose()[1], [0., 0.])

    def test_nearby_hostile_sound_cancels_early_exposure(self):
        for kind in ('gun', 'npc_gun', 'mortar', 'laser', 'lightning'):
            with self.subTest(kind=kind):
                self.obs['sounds'] = [dict(kind=kind, dist='near', bearing=0., age=.1)]
                self.assertEqual(self.choose()[1], [0., 0.])
        self.obs['sounds'] = [dict(kind='gun', dist='far', bearing=0., age=.1)]
        self.assertEqual(self.choose()[1], [145., 0.])

    def test_damage_and_projectile_cause_preservation(self):
        self.obs['events'] = [dict(type='damaged', amount=20, weapon='gun', bearing=0.)]
        self.assertEqual(self.choose()[1], [0., 0.])
        self.obs['events'] = []
        self.obs['projectiles'] = [dict(kind='gun', pos=[30., 0., 5.], vel=[-252., 0., 0.])]
        self.assertEqual(self.choose()[1], [0., 0.])

    def test_opponent_or_low_health_prevents_staging(self):
        self.obs['mechs'] = [dict(id=5, kind='mech', pos=[80., 0., 0.],
                                 vel=[0., 0., 0.], aim=[3.14, 0.],
                                 hp=1400, cubes=0, weapons=['gun'])]
        self.assertEqual(self.choose()[1], [0., 0.])
        self.obs['mechs'] = []
        self.obs['self']['hp'] = self.obs['self']['max_hp'] * .60
        self.assertEqual(self.choose()[1], [0., 0.])

    def test_zone_urgency_or_future_outside_veto(self):
        self.obs['self']['in_zone'] = False
        self.assertEqual(self.choose()[1], [0., 0.])
        self.obs['self']['in_zone'] = True
        self.obs['zone']['next_radius'] = 125.
        self.assertEqual(self.choose()[1], [0., 0.])

    def test_blocked_initial_path_prevents_reckless_charge(self):
        self.world.can_walk = False
        self.assertEqual(self.choose()[1], [0., 0.])
        self.assertEqual(self.world.calls, 1)

    def test_avoids_roof_mismatch_and_unreasonable_range(self):
        self.obs['drops'][0]['pos'][2] = 30.
        self.assertEqual(self.choose()[1], [0., 0.])
        self.obs['drops'][0]['pos'] = [230., 0., 0.]
        self.assertEqual(self.choose()[1], [0., 0.])

    def test_closer_of_two_safe_drops_is_selected(self):
        self.obs['drops'].append(dict(id=20001, pos=[110., 15., 0.],
                                      lands_in=14., radius=8., capture_s=4.,
                                      progress=0., holder=None))
        self.assertEqual(self.choose()[1], [110., 15.])


if __name__ == '__main__':
    unittest.main()
