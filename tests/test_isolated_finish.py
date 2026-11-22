"""[ASTRA_ENHANCEMENT_2026-11-21] Validate mode transitions for real and apparent crossfire."""
import math
import unittest
from types import SimpleNamespace
from test_agent import recording
from agent.observation import Observer
from agent.strategy import Strategy


class IsolatedFinishTests(unittest.TestCase):
    def setUp(self):
        h,frames=recording()
        self.o=frames[0]
        self.me=self.o['self']
        self.me.update(pos=[0,0,0],aim=[math.pi/2,0],hp=1200,max_hp=1400,energy=90,in_zone=True)
        self.gun=self.me['weapons'][0]
        self.gun.update(ammo=10,reload=0,cooldown=0)
        a=dict(id=3,kind='mech',pos=[0,66,0],vel=[0,0,0],aim=[0,0],hp=130,cubes=0,weapons=['gun'])
        b=dict(a,id=5,pos=[86,0,0],hp=1350)
        self.o.update(t=20,events=[],mechs=[a,b],zone=dict(center=[0,0],next_center=[0,0],
                      radius=300,next_radius=240,shrink_start=60,shrink_end=100))
        self.world=SimpleNamespace(ground=lambda *_:0,clear=lambda a,b:a[0]<60,walkable=lambda *_:True)
        self.strategy=Strategy(self.world,h['config'])
        self.observer=Observer()

    def mode(self):
        return self.strategy.choose(self.observer.parse(self.o))

    def test_screened_rival_and_finishing_magazine(self):
        self.assertEqual(self.mode(),'balanced')
        self.gun['ammo']=3
        self.assertEqual(self.mode(),'conservative')

    def test_open_second_shooter_or_exposed_flank_blocks_finish(self):
        self.world.clear=lambda *_:True
        self.assertEqual(self.mode(),'conservative')
        self.world.clear=lambda a,b:a[0]<60 or abs(a[1])>5
        self.assertEqual(self.mode(),'conservative')

    def test_energy_health_or_active_laser_preserve_retreat(self):
        self.me['energy']=8
        self.assertEqual(self.mode(),'conservative')
        self.me['energy']=90
        self.me['hp']=700
        self.assertEqual(self.mode(),'conservative')
        self.me['hp']=1200
        self.o['mechs'][0]['charging']=True
        self.assertEqual(self.mode(),'conservative')

    def test_third_contact_keeps_original_crowd_mode(self):
        self.o['mechs'].append(dict(self.o['mechs'][0],id=6,pos=[170,0,0]))
        self.assertEqual(self.mode(),'conservative')
