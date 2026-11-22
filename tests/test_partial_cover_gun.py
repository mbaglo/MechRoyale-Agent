"""[CHATGPT_ENHANCEMENT_2026-11-22] Ballistic gun peeking regression tests.

The cases exercise *decision correctness* against deliberately simple synthetic
cover rays. They are not competitive matches or authoritative wall physics.
"""
import copy
import math
import unittest

from agent.policy import Bot
from test_agent import recording


class LowerCover:
    """[CHATGPT_ENHANCEMENT_2026-11-22] Model a waist-high occluding wall."""
    def __init__(self, threshold, max_x=None, lead_y=None):
        self.threshold = threshold
        self.max_x = max_x
        self.lead_y = lead_y

    def clear(self, start, target):
        if self.max_x is not None and target[0] > self.max_x:
            return True
        if self.lead_y is not None and abs(target[1]-self.lead_y) > .4:
            return False
        return target[2] >= self.threshold


class PartialCoverGunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hello, frames = recording()
        cls.template = frames[0]

    def setUp(self):
        """[CHATGPT_ENHANCEMENT_2026-11-22] Controlled health and arena."""
        self.bot = Bot(copy.deepcopy(self.hello))
        o = self.obs = copy.deepcopy(self.template)
        for key in ('events','sounds','projectiles','cubes','crates',
                    'drops','pickups','mechs'):
            o[key] = []
        o['t'] = 10.
        o['self']['hp'] = o['self']['max_hp']
        o['self']['in_zone'] = True
        o['self']['weapons'][0]['ammo'] = 12
        o['self']['weapons'][0]['cooldown'] = 0
        o['self']['weapons'][0]['reload'] = 0
        o['self']['weapons'][1] = None
        pos=o['self']['pos']
        o['zone'] = dict(center=pos[:2], next_center=pos[:2],
                         radius=500, next_radius=350,
                         shrink_start=60, shrink_end=110, dps=20)
        self.h = self.hello['config']['mech']['height']
        self.enemy = dict(id=5,kind='mech',pos=[pos[0]+75,pos[1],pos[2]],
                          vel=[0.,0.,0.], hp=100, max_hp=1400,
                          weapons=['gun'],aim=[math.pi,0.])
        o['mechs'] = [self.enemy]
        self.bot.combat.world=LowerCover(pos[2]+self.h*.67)

    def test_shoot_exposed_upper_mech_when_center_is_blocked(self):
        """[CHATGPT_FIX_2026-11-22] Aim at shootable upper cylinder."""
        me=self.obs['self']
        origin=[*me['pos'][:2],me['pos'][2]+me['stats']['muzzle_height']]
        center=[*self.enemy['pos'][:2],self.enemy['pos'][2]+self.h*.5]
        self.assertFalse(self.bot.combat.world.clear(origin,center))
        a=self.bot.act(self.obs)
        self.assertEqual(self.bot.combat.target_id,5)
        center_pitch=math.atan2(center[2]-origin[2],75)
        self.assertGreater(a['aim'][1],center_pitch+.02)
        self.obs['self']['aim'] = a['aim']
        self.obs['t']+=.1
        self.obs['tick']+=2
        b=self.bot.act(self.obs)
        self.assertEqual(b['fire'],[True,False])

    def test_preserve_center_target_when_unoccluded(self):
        """[CHATGPT_FIX_2026-11-22] Direct-center aim remains original."""
        self.bot.combat.world=LowerCover(-float('inf'))
        a=self.bot.act(self.obs)
        me=self.obs['self']
        origin_z=me['pos'][2]+me['stats']['muzzle_height']
        expected=math.atan2(self.enemy['pos'][2]+self.h*.5-origin_z,75)
        self.assertAlmostEqual(a['aim'][1],expected,places=5)

    def test_no_shot_through_unshootable_cover(self):
        """[CHATGPT_FIX_2026-11-22] Block all body and lead rays."""
        self.bot.combat.world=LowerCover(self.enemy['pos'][2]+self.h+25)
        a=self.bot.act(self.obs)
        self.assertEqual(a['fire'],[False,False])
        self.assertIsNone(self.bot.combat.target_id)

    def test_no_shot_when_projected_upper_lead_hits_cover(self):
        """[CHATGPT_FIX_2026-11-22] Validate lead ray, not last-seen ray."""
        self.enemy['vel']=[0.,18.,0.]
        self.bot.combat.world=LowerCover(self.enemy['pos'][2]+self.h*.67,
                                         lead_y=self.enemy['pos'][1])
        a=self.bot.act(self.obs)
        self.assertEqual(a['fire'],[False,False])
        self.assertIsNone(self.bot.combat.target_id)

    def test_direct_center_has_priority_over_secondary_upper_target(self):
        """[CHATGPT_FIX_2026-11-22] Preserve original whole-target preference."""
        second=copy.deepcopy(self.enemy)
        second.update(id=6,pos=[self.enemy['pos'][0]+25,
                                self.enemy['pos'][1]+20,self.enemy['pos'][2]])
        self.obs['mechs']=[self.enemy,second]
        self.bot.combat.world=LowerCover(self.enemy['pos'][2]+self.h*.67,
                                         max_x=self.enemy['pos'][0]+15)
        self.bot.act(self.obs)
        self.assertEqual(self.bot.combat.target_id,6)

    def test_upper_gun_does_not_trigger_secondary_weapon(self):
        """[CHATGPT_FIX_2026-11-22] Do not fire a mortar from gun peek aim."""
        self.obs['self']['weapons'][1]=dict(
            kind='mortar',cooldown=0,
            stats=copy.deepcopy(self.hello['config']['weapons']['mortar']))
        a=self.bot.act(self.obs)
        self.obs['self']['aim'] = a['aim']
        self.obs['t']+=.1
        self.obs['tick']+=2
        b=self.bot.act(self.obs)
        self.assertEqual(b['fire'],[True,False])


if __name__ == '__main__':
    unittest.main()
