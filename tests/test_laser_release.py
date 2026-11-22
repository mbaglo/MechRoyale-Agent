"""[ASTRA_FIX_2026-11-21] Verify release decisions against actual torso direction and game geometry."""
import math
import unittest
from types import SimpleNamespace

from test_agent import recording
from agent.observation import Observer
from agent.combat import Combat, laser_contact


class LaserReleaseTests(unittest.TestCase):
    def setUp(self):
        h,frames=recording()
        self.o=frames[0]
        self.o.update(t=12,sounds=[],events=[],crates=[])
        self.me=self.o['self']
        self.me.update(pos=[0,0,0],aim=[0,0])
        spec=h['config']['weapons']['laser']
        self.me['weapons'][1]=dict(kind='laser',cooldown=0,charge=spec['charge'],stats=spec)
        self.e=dict(id=8,kind='mech',pos=[100,0,0],vel=[0,0,0],hp=1400,cubes=0)
        self.o['mechs']=[self.e]
        self.world=SimpleNamespace(clear=lambda *_:True)
        self.combat=Combat(h['config'],self.world)
        self.observer=Observer()

    def holding(self):
        return self.combat.act(self.observer.parse(self.o),'balanced')[1][1]

    def test_hold_when_old_center_tolerance_would_miss(self):
        self.me['aim']=[.032,math.atan2(4.5-7,100)]
        self.assertTrue(self.holding())
        self.me['aim'][0]=.018
        self.assertFalse(self.holding())

    def test_release_visible_upper_body_and_respect_wall(self):
        self.e['pos'][0]=38
        self.me['aim']=[0,math.atan2(8-7,38)]
        self.assertFalse(self.holding())
        self.world.clear=lambda a,b:b[2]<7.5
        self.assertTrue(self.holding())

    def test_use_scaled_cylinder_and_never_release_early(self):
        self.me['aim']=[.03,0]
        self.assertTrue(self.holding())
        self.e['cubes']=8
        self.assertFalse(self.holding())
        self.me['weapons'][1]['charge']=.3
        self.assertTrue(self.holding())

    def test_clipping_and_vertical_intersections(self):
        self.assertIsNone(laser_contact([0,0,7],[0,0],[100,0,0],2.5,9,85))
        self.assertIsNone(laser_contact([0,0,7],[math.pi,0],[100,0,0],2.5,9,280))
        hit=laser_contact([0,0,0],[0,math.pi/2],[0,0,10],2.5,9,40)
        self.assertAlmostEqual(hit[2],10)
