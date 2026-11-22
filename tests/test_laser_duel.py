"""[ASTRA_ENHANCEMENT_2026-11-21] Verify that recorded laser cues control paired ground positions."""
import math
import unittest
from types import SimpleNamespace

from agent.laser_duel import LaserDuel
from agent.observation import Observer
from test_agent import recording


class LaserDuelTests(unittest.TestCase):
    def setUp(self):
        h,frames=recording()
        self.o=frames[0]
        self.me=self.o['self']
        self.me.update(pos=[0,0,0],grounded=True,in_zone=True)
        self.me['weapons'][0].update(reload=0,ammo=12)
        self.e=dict(id=8,kind='mech',pos=[110,0,0],vel=[0,0,0],aim=[math.pi,0],hp=1000,weapons=['gun','laser'])
        self.o.update(t=10,beams=[],events=[],drops=[],mechs=[self.e],
                      zone=dict(center=[0,0],next_center=[0,0],radius=300,next_radius=250,shrink_end=110))
        def clear(a,b):
            return (b[1] if a[0]>80 else a[1]) >= -1
        self.world=SimpleNamespace(clear=clear,ground=lambda *_:0,walkable=lambda *_:True)
        self.duel=LaserDuel(self.world,h['config'])
        self.observer=Observer()

    def goal(self):
        return self.duel.goal(self.observer.parse(self.o))

    def test_observed_shot_then_hide_in_time_for_next_charge(self):
        self.assertIsNone(self.goal())
        self.o['beams']=[dict(by=8,kind='laser',age=.05)]
        self.assertGreaterEqual(self.goal()[1],-1)
        self.o['beams']=[]
        self.o['t']+=1.4
        self.assertLess(self.goal()[1],-1)
        self.o['t']+=2
        self.assertIsNone(self.goal())

    def test_charge_or_empty_gun_uses_sheltered_side(self):
        self.e['charging']=True
        self.assertLess(self.goal()[1],-1)
        self.e['charging']=False
        self.me['weapons'][0]['ammo']=0
        self.o['events']=[dict(type='damaged',weapon='laser',by=8,amount=315,bearing=0)]
        self.assertLess(self.goal()[1],-1)

    def test_skip_urgent_capture_and_missing_shelter(self):
        self.e['charging']=True
        self.me['in_zone']=False
        self.assertIsNone(self.goal())
        self.me['in_zone']=True
        self.o['drops']=[dict(holder=self.me['id'])]
        self.assertIsNone(self.goal())
        self.o['drops']=[]
        self.world.clear=lambda *_:True
        self.assertIsNone(self.goal())
