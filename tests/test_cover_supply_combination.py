"""[CHATGPT_FIX_2026-11-21] Integration tests for 2.92 supply and 2.81 shelter.

Tests policy precedence, not simulated match outcomes.
"""
import copy
import unittest

from test_agent import recording
from agent.policy import Bot


class CoverSupplyCombinationTests(unittest.TestCase):
    def setUp(self):
        hello, observations = recording()
        self.bot = Bot(hello)
        self.obs = copy.deepcopy(observations[0])
        self.obs['t'] = 22.
        self.obs['mechs'] = []
        self.obs['projectiles'] = []
        self.obs['events'] = []
        self.obs['sounds'] = []
        self.obs['crates'] = []
        self.obs['pickups'] = []
        self.obs['cubes'] = []
        self.obs['drops'] = []
        me = self.obs['self']
        me['in_zone'] = True
        me['grounded'] = True
        me['vel'] = [0., 0., 0.]
        p = me['pos']
        self.obs['zone'] = {
            'center':p[:2], 'radius':450.,
            'next_center':p[:2], 'next_radius':250.,
            'shrink_start':60., 'shrink_end':120., 'dps':20.
        }

    def test_supply_finishing_precedes_recovery_cover(self):
        """[CHATGPT_FIX_2026-11-21] Do not interrupt a nearly won supply capture."""
        p = list(self.obs['self']['pos'])
        self.obs['drops'] = [{
            'id':20001, 'pos':p, 'radius':8.,
            'holder':self.obs['self']['id'],
            'progress':3.5, 'capture_s':4., 'lands_in':0.
        }]
        def forbidden_route(s):
            raise AssertionError('shelter must not interrupt finishing drop')
        self.bot.recovery_cover.route = forbidden_route
        action = self.bot.act(self.obs)
        self.assertEqual(action['tick'], self.obs['tick'])

    def test_covered_recovery_holds_position_when_no_supply_claim(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Preserve scored cover hold."""
        self.bot.recovery_cover.route = lambda s: (None, True)
        action = self.bot.act(self.obs)
        self.assertEqual(action['move'], [0., 0.])
        self.assertFalse(action['boost'])

    def test_cover_destination_passes_to_original_navigation(self):
        """[CHATGPT_FIX_2026-11-21] Shelter and zone detour controls are distinct."""
        p = self.obs['self']['pos']
        goal = [p[0]+12., p[1]]
        self.bot.recovery_cover.route = lambda s: (goal, False)
        captured = {}
        def navigation(s, requested, mode, zone_detour=False):
            captured['goal'] = requested
            captured['zone_detour'] = zone_detour
            return [1.,0.], False
        self.bot.navigator.move = navigation
        self.bot.act(self.obs)
        self.assertEqual(captured['goal'], goal)
        self.assertFalse(captured['zone_detour'])


if __name__ == '__main__':
    unittest.main()
