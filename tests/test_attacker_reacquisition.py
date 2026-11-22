"""[ASTRA_ENHANCEMENT_2026-11-21] Lost-track bearing, uncertainty, and stronger observations."""
import math
import unittest
from types import SimpleNamespace
from test_agent import recording
from agent.combat import Combat,angle_delta
from agent.observation import Observer


class AttackerReacquisitionTests(unittest.TestCase):
    def setUp(self):
        h,frames=recording()
        self.o=frames[0]
        self.me=self.o['self']
        self.me.update(pos=[0,0,0],aim=[0,0],in_zone=True)
        self.e=dict(kind='mech',id=9,pos=[0,140,0],vel=[0,0,0],aim=[0,0],hp=1100)
        self.o.update(t=10,mechs=[self.e],events=[dict(type='hit',target=9,weapon='gun',amount=45)],
                      zone=dict(center=[0,0],next_center=[0,0],radius=300,next_radius=200,shrink_end=100),
                      crates=[],sounds=[])
        self.observer=Observer()
        self.combat=Combat(h['config'],SimpleNamespace(clear=lambda *_:False))
        self.act()
        self.o.update(t=13,mechs=[],events=[],sounds=[])

    def act(self):
        return self.combat.act(self.observer.parse(self.o),'balanced')

    def test_face_last_observed_attacker_without_firing(self):
        aim,fire,_=self.act()
        self.assertAlmostEqual(aim[0],math.pi/2)
        self.assertFalse(any(fire))
        self.o['sounds']=[dict(kind='gun',dist='far',bearing=-1.4)]
        self.assertAlmostEqual(self.act()[0][0],math.pi/2)
        self.o['sounds'][0]['dist']='near'
        self.assertAlmostEqual(self.act()[0][0],-1.4)

    def test_kill_and_timeout_release_bearing(self):
        self.o['events']=[dict(type='kill',target=9)]
        self.assertAlmostEqual(self.act()[0][0],angle_delta(13*.6,0))
        self.setUp()
        self.o['t']=15.1
        self.assertAlmostEqual(self.act()[0][0],angle_delta(15.1*.6,0))

    def test_uncertain_close_track_and_ambiguous_opponents(self):
        self.me['pos']=[0,80,0]
        self.o['t']=14
        self.assertAlmostEqual(self.act()[0][0],angle_delta(14*.6,0))
        self.me['pos']=[0,0,0]
        self.o.update(mechs=[dict(self.e,id=5)],events=[dict(type='hit',target=5,amount=45)])
        self.act()
        self.o.update(t=14.1,mechs=[],events=[])
        self.assertIsNone(self.observer.parse(self.o).last_opponent)
