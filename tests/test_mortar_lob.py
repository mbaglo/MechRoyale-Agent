"""[CHATGPT_FIX_2026-11-21] Mortar cover and ballistic regressions.

These are geometry/decision tests, NOT full-match outcomes. The official scorer
remains the only evidence of placement improvement.
"""
import copy
import math
from types import SimpleNamespace
import unittest

from test_agent import recording
from agent.combat import Combat
from agent.mortar_lob import mortar_lob_solution
from agent.observation import Observer


class WallWorld:
    """Simple rectangular high/low wall, not a simulated game map."""
    def __init__(self, wall_height=18.):
        self.wall_height = wall_height

    def ground(self, x, y):
        return 0.

    def solid(self, x, y, z):
        return 38. <= x <= 42. and -8. <= y <= 8. and 0. <= z <= self.wall_height

    def clear(self, start, end):
        for i in range(1, 101):
            t = i/100.
            point = [start[k]+(end[k]-start[k])*t for k in range(3)]
            if self.solid(*point) or point[2] < 0:
                return False
        return True


class MortarCoverTests(unittest.TestCase):
    def setUp(self):
        hello, frames = recording()
        self.hello = hello
        self.obs = copy.deepcopy(frames[0])
        self.obs.update(t=12., events=[], sounds=[], crates=[], projectiles=[],
                        mechs=[], pickups=[], drops=[])
        me = self.obs['self']
        me.update(pos=[0., 0., 0.], hp=1400., max_hp=1400., energy=100.,
                  grounded=True, in_zone=True)
        # [CHATGPT_ENHANCEMENT_2026-11-21] Explicitly exercise a pitch
        # envelope with a legal high arc; real match limits always control.
        me['stats'].update(height=9., radius=2.5, muzzle_height=7.,
                           min_pitch=-.6, max_pitch=1.5, turn_rate=4.)
        self.weapon = dict(kind='mortar', cooldown=0.,
                           stats=copy.deepcopy(hello['config']['weapons']['mortar']))
        self.obs['self']['weapons'] = [
            dict(kind='gun', cooldown=0, ammo=12, reload=0,
                 stats=copy.deepcopy(hello['config']['weapons']['gun'])),
            self.weapon
        ]
        self.obs['zone'] = dict(center=[0.,0.], radius=400.,
                                next_center=[0.,0.], next_radius=280.,
                                shrink_start=60., shrink_end=120., dps=20.)
        self.world = WallWorld()
        self.obs['mechs'] = [{
            'kind':'mech', 'id':3, 'pos':[100.,0.,0.],
            'vel':[0.,0.,0.], 'hp':1000., 'max_hp':1400.,
            'weapons':['gun'], 'aim':[math.pi,0.]
        }]

    def test_high_arc_lobs_over_wall_when_direct_ray_is_blocked(self):
        """[CHATGPT_FIX_2026-11-21] Covered-target mortar is no longer vetoed."""
        me, target = self.obs['self'], self.obs['mechs'][0]
        origin = [0.,0.,me['stats']['muzzle_height']]
        center = [100.,0.,4.5]
        self.assertFalse(self.world.clear(origin,center))
        lob = mortar_lob_solution(me,target,self.world,self.weapon['stats'])
        self.assertIsNotNone(lob)
        self.assertGreater(lob[1], .45)
        self.assertAlmostEqual(lob[0],0.,places=3)

    def test_high_arc_leads_laterally_moving_target(self):
        """[CHATGPT_FIX_2026-11-21] Do not reuse low-arc flight time."""
        enemy = self.obs['mechs'][0]
        enemy['vel'] = [0., 5., 0.]
        lob = mortar_lob_solution(
            self.obs['self'], enemy, self.world, self.weapon['stats']
        )
        self.assertIsNotNone(lob)
        # High-angle rounds remain airborne longer than direct gun shots.
        self.assertGreater(lob[0], .08)

    def test_unreachable_high_wall_is_rejected(self):
        """[CHATGPT_FIX_2026-11-21] Never claim ballistic feasibility through rock."""
        self.world.wall_height = 200.
        self.assertIsNone(mortar_lob_solution(
            self.obs['self'],self.obs['mechs'][0],self.world,self.weapon['stats']
        ))

    def test_prefer_mortar_when_no_direct_weapon_shot_exists(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Aim and fire only a validated arc."""
        observer = Observer()
        combat = Combat(self.hello['config'],self.world)
        aim,fire,_ = combat.act(observer.parse(self.obs),'balanced')
        self.assertGreater(aim[1],.45)
        self.assertEqual(fire,[False,False])
        self.obs['self']['aim'] = aim
        _,fire,_ = combat.act(observer.parse(self.obs),'balanced')
        self.assertEqual(fire,[False,True])

    def test_preserve_original_direct_target_preference(self):
        """[CHATGPT_FIX_2026-11-21] The old target-firing pipeline remains."""
        self.world.wall_height = 0.
        observer = Observer()
        combat = Combat(self.hello['config'],self.world)
        target = self.obs['mechs'][0]
        aim,fire,_ = combat.act(observer.parse(self.obs),'balanced')
        self.assertLess(aim[1],.45)
        self.assertEqual(combat.target_id,target['id'])

    def test_no_unsafe_lob_under_conservative_retreat(self):
        """[CHATGPT_FIX_2026-11-21] Preserve original retreat protection."""
        combat=Combat(self.hello['config'],self.world)
        observer=Observer()
        aim,fire,_=combat.act(observer.parse(self.obs),'conservative')
        self.assertEqual(fire,[False,False])

    def test_invalid_pitch_is_rejected(self):
        """[CHATGPT_FIX_2026-11-21] Live mech pitch limits always win."""
        self.obs['self']['stats']['max_pitch']=.05
        self.assertIsNone(mortar_lob_solution(
            self.obs['self'],self.obs['mechs'][0],self.world,self.weapon['stats']
        ))


if __name__=='__main__':
    unittest.main()
