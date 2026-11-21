"""[CHATGPT_FIX_2026-11-21] Safe NPC power-cube opportunity regressions.

These are tactical unit tests, NOT match simulation or evidence of a higher
official score. Keep all V1/EXP-012 assertions unchanged.
"""
import copy
import math
from types import SimpleNamespace
import unittest

from test_agent import recording
from agent.observation import Observer
from agent.combat import Combat


class NpcCubeOpportunityTests(unittest.TestCase):
    def setUp(self):
        hello, observations = recording()
        self.config = hello['config']
        self.obs = copy.deepcopy(observations[0])
        self.obs.update(t=15, events=[], sounds=[], mechs=[], crates=[])
        self.obs['self'].update(
            pos=[0., 0., 0.], hp=1400., max_hp=1400., energy=100.,
            in_zone=True, aim=[0., 0.]
        )
        self.obs['self']['weapons'] = [
            dict(kind='gun', cooldown=0, ammo=12, reload=0,
                 stats=copy.deepcopy(self.config['weapons']['gun'])),
            None
        ]
        self.obs['zone'] = {
            'center':[0,0], 'radius':400, 'next_center':[0,0],
            'next_radius':250, 'shrink_start':60, 'shrink_end':110, 'dps':20
        }
        self.world = SimpleNamespace(clear=lambda a, b: True)
        self.combat = Combat(self.config, self.world)
        self.observer = Observer()

    def drone(self, dist=120):
        return dict(
            id=105, kind='npc', pos=[float(dist), 0., 0.],
            vel=[0., 0., 0.], aim=[math.pi, 0.],
            hp=350., max_hp=350.
        )

    def situation(self):
        return self.observer.parse(self.obs)

    def test_safe_drone_aim_uses_npc_center_and_fires(self):
        """[CHATGPT_FIX_2026-11-21] Aim at 1.75m NPC center, not 4.5m mech center."""
        self.obs['mechs'] = [self.drone()]
        aim, fire, _ = self.combat.act(self.situation(), 'balanced')
        expected_pitch = math.atan2(
            1.75 - self.obs['self']['stats']['muzzle_height'], 120.
        )
        self.assertAlmostEqual(aim[0], 0., places=5)
        self.assertAlmostEqual(aim[1], expected_pitch, places=5)
        self.obs['self']['aim'] = aim
        self.assertTrue(self.combat.act(self.situation(), 'balanced')[1][0])

    def test_player_contact_takes_priority_over_drone(self):
        """[CHATGPT_FIX_2026-11-21] Farming never displaces a visible mech."""
        self.obs['mechs'] = [
            self.drone(),
            dict(id=3, kind='mech', pos=[145., 0., 0.], vel=[0.,0.,0.],
                 hp=1400., max_hp=1400., aim=[math.pi,0.], weapons=['gun'])
        ]
        self.combat.act(self.situation(), 'balanced')
        self.assertEqual(self.combat.target_id, 3)

    def test_no_farming_while_hurt_or_under_attack(self):
        """[CHATGPT_FIX_2026-11-21] Protect quiet HP regeneration opportunities."""
        self.obs['mechs'] = [self.drone()]
        self.obs['self']['hp'] = 900.
        self.assertEqual(self.combat.act(self.situation(),'balanced')[1],[False,False])
        self.obs['self']['hp'] = 1400.
        self.obs['events'] = [dict(type='damaged',amount=25,weapon='npc',
                                  bearing=0,by=105)]
        self.assertEqual(self.combat.act(self.situation(),'balanced')[1],[False,False])

    def test_no_drone_farming_at_close_range_or_with_low_ammo(self):
        """[CHATGPT_FIX_2026-11-21] Avoid walking into 45m drone retaliation."""
        self.obs['mechs'] = [self.drone(40)]
        self.assertIsNone(self.combat.act(self.situation(),'balanced')[1][0]
                          or None)
        self.obs['mechs'] = [self.drone(120)]
        self.obs['self']['weapons'][0]['ammo'] = 4
        self.combat.act(self.situation(),'balanced')
        self.assertNotEqual(self.combat.target_id,105)

    def test_conservative_and_zone_urgent_do_not_farm(self):
        """[CHATGPT_FIX_2026-11-21] Preserve retreat/zone priority."""
        self.obs['mechs'] = [self.drone()]
        self.combat.act(self.situation(),'conservative')
        self.assertNotEqual(self.combat.target_id,105)
        self.obs['self']['in_zone'] = False
        self.combat.act(self.situation(),'balanced')
        self.assertNotEqual(self.combat.target_id,105)

    def test_secondary_weapons_preserved_for_real_engagements(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Do not spend laser charge on an NPC."""
        self.obs['mechs'] = [self.drone()]
        self.obs['self']['weapons'][1] = dict(
            kind='laser', cooldown=0, charge=0,
            stats=copy.deepcopy(self.config['weapons']['laser'])
        )
        aim,fire,_ = self.combat.act(self.situation(),'balanced')
        self.obs['self']['aim'] = aim
        aim,fire,_ = self.combat.act(self.situation(),'balanced')
        self.assertTrue(fire[0])
        self.assertFalse(fire[1])


if __name__ == '__main__':
    unittest.main()
