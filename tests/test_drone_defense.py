"""[ASTRA_ENHANCEMENT_2026-11-21] Exercise resource combat through the authoritative action function."""
import math
import unittest
from test_agent import recording
from agent.policy import Bot


class DroneDefenseTests(unittest.TestCase):
    def setUp(self):
        h,frames=recording()
        self.bot=Bot(h)
        self.o=frames[0]
        for field in ('events','sounds','mechs','crates','drops','pickups','cubes','projectiles'):
            self.o[field]=[]
        self.o.update(t=10,zone=dict(center=[0,0],next_center=[0,0],radius=250,next_radius=150,
                                     shrink_start=60,shrink_end=110,dps=20))
        self.me=self.o['self']
        self.me.update(pos=[0,0,0],hp=1400,max_hp=1400,grounded=True,in_zone=True)
        self.drone=dict(id=102,kind='npc',pos=[32,0,0],vel=[0,0,0],aim=[math.pi,0],hp=350)
        self.o['mechs']=[self.drone]
        self.gun=self.me['weapons'][0]
        self.gun.update(ammo=12,reload=0,cooldown=0)
        self.me['aim']=[0,math.atan2(1.75-self.me['stats']['muzzle_height'],32)]
        self.bot.world.clear=lambda *_:True
        self.bot.world.walkable=lambda *_:True

    def test_take_complete_engagement_without_midburst_reload(self):
        self.gun['ammo']=8
        shots=0
        while self.drone['hp']>0 and shots<12:
            a=self.bot.act(self.o)
            self.assertTrue(a['fire'][0])
            self.assertFalse(a['reload'])
            self.assertAlmostEqual(a['aim'][1],self.me['aim'][1])
            shots+=1
            self.gun['ammo']-=1
            self.drone['hp']-=self.gun['stats']['damage']
            self.o['t']+=self.gun['stats']['cooldown']
        self.assertEqual(shots,8)

    def test_reject_insufficient_magazine_and_risky_resources(self):
        self.gun['ammo']=7
        self.assertFalse(any(self.bot.act(self.o)['fire']))
        self.gun['ammo']=12
        self.o['zone']['next_radius']=22
        self.assertFalse(any(self.bot.act(self.o)['fire']))
        self.o['zone']['next_radius']=150
        self.bot.world.walkable=lambda *_:False
        self.assertFalse(any(self.bot.act(self.o)['fire']))

    def test_opponent_priority_and_sounds(self):
        self.o['sounds']=[dict(kind='gun',bearing=2,dist='near',age=0)]
        self.assertFalse(any(self.bot.act(self.o)['fire']))
        self.o['sounds']=[]
        self.o['mechs'].append(dict(id=6,kind='mech',pos=[0,80,0],vel=[0,0,0],hp=1000,cubes=0,aim=[0,0]))
        self.assertAlmostEqual(self.bot.act(self.o)['aim'][0],math.pi/2)

    def test_no_attacks_on_distant_or_multiple_drones(self):
        self.drone['pos'][0]=60
        self.assertFalse(any(self.bot.act(self.o)['fire']))
        self.drone['pos'][0]=32
        self.o['mechs'].append(dict(self.drone,id=103))
        self.assertFalse(any(self.bot.act(self.o)['fire']))
