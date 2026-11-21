"""[ASTRA_ENHANCEMENT_2026-11-21] Exercise coordinated decisions via the match entry point."""
import copy
import math
import unittest

from agent.policy import Bot
from test_agent import recording


class EngagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hello, stream = recording()
        cls.first = stream[0]

    def setUp(self):
        self.bot = Bot(self.hello)
        self.bot.world.walkable = lambda *_: True
        self.bot.world.clear = lambda *_: True
        self.obs = copy.deepcopy(self.first)
        self.obs.update(t=10, events=[], sounds=[], projectiles=[], cubes=[], crates=[], pickups=[], drops=[])
        self.obs['self'].update(pos=[0, 0, 0], hp=1400, max_hp=1400, in_zone=True, aim=[0, 0])
        self.obs['self']['weapons'][0].update(ammo=12, reload=0, cooldown=0)
        self.obs['self']['weapons'][1] = None
        self.obs['zone'].update(center=[0, 0], radius=400, next_center=[0, 0], next_radius=300, shrink_end=100)

    def enemy(self, number, x, y, hp):
        return dict(id=number, pos=[x,y,0], kind='mech', hp=hp, vel=[0,0,0],
                    aim=[0,0], weapons=['gun'])

    def test_focus_fire_opportunity_with_two_attackers(self):
        self.obs['mechs'] = [self.enemy(3, 25, 0, 1400), self.enemy(4, 0, 85, 40)]
        action = self.bot.act(self.obs)
        self.assertEqual(self.bot.combat.target_id, 4)
        self.assertAlmostEqual(action['aim'][0], math.pi/2)
        self.assertEqual(self.bot.mode, 'aggressive')
        self.assertGreater(action['move'][1], 0)
        self.assertFalse(action['fire'][0])  # Torso has not completed the turn.

    def test_reload_window_and_zone_take_precedence(self):
        self.obs['mechs'] = [self.enemy(3, 25, 0, 1400), self.enemy(4, 0, 85, 40)]
        self.obs['self']['weapons'][0].update(ammo=0, reload=2.4)
        self.bot.act(self.obs)
        self.assertEqual(self.bot.mode, 'conservative')
        self.obs['self']['weapons'][0].update(ammo=12, reload=0)
        self.obs['self']['in_zone'] = False
        self.bot.act(self.obs)
        self.assertEqual(self.bot.mode, 'conservative')

    def test_occluded_contacts_do_not_trigger_crossfire_or_divert_aim(self):
        self.obs['mechs'] = [self.enemy(3, 25, 0, 20), self.enemy(4, 0, 85, 1400)]
        self.bot.world.clear = lambda start, end: end[0] < 20
        self.bot.act(self.obs)
        self.assertEqual(self.bot.combat.target_id, 4)
        self.assertEqual(self.bot.mode, 'balanced')
