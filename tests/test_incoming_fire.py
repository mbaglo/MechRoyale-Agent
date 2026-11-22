"""[CHATGPT_FIX_2026-11-22] Incoming-fire idle and gravity regressions.

Synthetic immediate-action tests, not full-match simulations or evidence of
placement. Check that a quiet inner-zone goal cannot disable imminent evasion.
"""
import math
import unittest
from types import SimpleNamespace

from agent.incoming_fire import (
    mortar_impacts, incoming_bullet, explosive_risk, immediate_blast_warning
)
from agent.navigation import Navigator


class FlatWorld:
    def ground(self,x,y):
        return 0.
    def solid(self,x,y,z):
        return False
    def clear(self,start,end):
        return True
    def walkable(self,start,end,stats):
        return True


class WallWorld(FlatWorld):
    def clear(self,start,end):
        return False


class IncomingFireTests(unittest.TestCase):
    def setUp(self):
        """[CHATGPT_ENHANCEMENT_2026-11-22] Supply bounded official-like stats."""
        self.world = FlatWorld()
        self.config = {'weapons':{'mortar':{'gravity':22.,'splash_radius':7.}}}
        self.me = {
            'pos':[0.,0.,0.], 'vel':[0.,0.,0.], 'energy':80.,
            'stats':{'walk_speed':11.7,'boost_speed':19.5,'ground_accel':20.,
                     'height':9.,'radius':2.5},
        }
        self.obs = {
            't':20., 'projectiles':[], 'zone':{
                'center':[0.,0.], 'radius':500.,'next_center':[0.,0.],
                'next_radius':400.,'shrink_end':120.
            }
        }
        self.s = SimpleNamespace(me=self.me,obs=self.obs,enemies=[],urgent=False)

    def move(self,world=None):
        nav = Navigator(world or self.world,self.config)
        return nav.move(self.s,[0.,0.],'balanced')[0]

    def test_original_idle_is_retained_when_no_threat(self):
        """[CHATGPT_FIX_2026-11-22] Preserve quiet-safe behavior."""
        self.assertEqual(self.move(),[0.,0.])

    def test_visible_shell_falls_to_the_ground_with_gravity(self):
        """[CHATGPT_ENHANCEMENT_2026-11-22] 20m high + downward velocity."""
        p = {'kind':'mortar','pos':[0.,0.,20.],'vel':[0.,0.,-20.]}
        impacts = mortar_impacts([p],self.world,self.config,self.me)
        self.assertEqual(len(impacts),1)
        self.assertLess(impacts[0][0],.85)
        self.assertGreater(impacts[0][0],.65)
        self.assertTrue(immediate_blast_warning(self.me, impacts))

    def test_mortar_dodge_while_current_goal_is_already_reached(self):
        """[CHATGPT_FIX_2026-11-22] Avoid previously unconditional idle."""
        self.obs['projectiles']=[{'kind':'mortar','pos':[0.,0.,20.],
                                  'vel':[0.,0.,-20.]}]
        movement=self.move()
        self.assertGreater(math.hypot(*movement),.5)
        impacts=mortar_impacts(self.obs['projectiles'],
                               self.world,self.config,self.me)
        moving=explosive_risk(self.me['pos'],self.me['vel'],movement,
                              self.me['stats'],impacts,self.world)
        idle=explosive_risk(self.me['pos'],self.me['vel'],[0.,0.],
                            self.me['stats'],impacts,self.world)
        self.assertLess(moving,idle)

    def test_distant_mortar_impact_does_not_cause_false_escape(self):
        """[CHATGPT_FIX_2026-11-22] Ignore shell landing out of range."""
        self.obs['projectiles']=[{'kind':'mortar','pos':[100.,0.,20.],
                                  'vel':[0.,0.,-20.]}]
        self.assertEqual(self.move(),[0.,0.])

    def test_unreachable_mortar_still_in_flight_does_not_trigger(self):
        """[CHATGPT_FIX_2026-11-22] Limit warnings to 1.2 second horizon."""
        self.obs['projectiles']=[{'kind':'mortar','pos':[0.,0.,150.],
                                  'vel':[0.,0.,0.]}]
        impacts=mortar_impacts(self.obs['projectiles'],
                               self.world,self.config,self.me)
        self.assertFalse(impacts)
        self.assertEqual(self.move(),[0.,0.])

    def test_no_blast_penalty_when_opaque_cover_blocks_splash(self):
        """[CHATGPT_ENHANCEMENT_2026-11-22] Published walls block explosions."""
        impacts=[(.7,0.,0.,.4,7.)]
        self.assertEqual(
            explosive_risk(self.me['pos'],self.me['vel'],[0.,0.],
                           self.me['stats'],impacts,WallWorld()),0.)

    def test_approaching_gun_bullet_also_cancels_unsafe_idle(self):
        """[CHATGPT_FIX_2026-11-22] Straight incoming fire is never ignored."""
        self.obs['projectiles']=[{'kind':'gun','pos':[80.,0.,4.5],
                                  'vel':[-200.,0.,0.]}]
        self.assertTrue(incoming_bullet(self.obs['projectiles'],self.me))
        movement=self.move()
        self.assertGreater(math.hypot(*movement),.5)

    def test_no_reaction_to_receding_or_high_bullet(self):
        """[CHATGPT_FIX_2026-11-22] Do not chase irrelevant projectiles."""
        for pos,vel in [([80.,0.,4.5],[200.,0.,0.]),
                        ([80.,0.,35.],[-200.,0.,0.])]:
            with self.subTest(pos=pos,vel=vel):
                self.obs['projectiles']=[{'kind':'gun','pos':pos,'vel':vel}]
                self.assertFalse(incoming_bullet(self.obs['projectiles'],self.me))
                self.assertEqual(self.move(),[0.,0.])


if __name__=='__main__':
    unittest.main()
