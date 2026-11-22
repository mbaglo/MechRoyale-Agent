"""[ASTRA_ENHANCEMENT_2026-11-21] Verify completion and release of an observed capture."""
import math
import unittest
from test_agent import recording
from agent.policy import Bot
from agent.supply import finishing_drop


class SupplyFinishTests(unittest.TestCase):
    def setUp(self):
        h,frames=recording()
        self.config=h['config']
        self.bot=Bot(h)
        self.o=frames[0]
        for key in ('mechs','crates','cubes','pickups','sounds','events','projectiles','beams'):
            self.o[key]=[]
        self.me=self.o['self']
        self.me.update(pos=[6.5,0,0],vel=[0,0,0],in_zone=True,grounded=True,hp=800,max_hp=1400)
        self.o.update(t=80,zone=dict(center=[0,0],radius=260,next_center=[110,0],next_radius=90,
                                     shrink_start=125,shrink_end=170,dps=35))
        self.drop=dict(id=20001,pos=[0,0,0],radius=8,holder=self.me['id'],progress=2.9,capture_s=4,
                       lands_in=0)
        self.o['drops']=[self.drop]
        self.bot.world.clear=lambda *_:True
        self.bot.world.walkable=lambda *_:True
        self.enemy=dict(id=9,kind='mech',pos=[-55,0,0],vel=[0,0,0],aim=[0,0],hp=1000,weapons=['gun'])
        self.o['mechs']=[self.enemy]

    def finishable(self):
        return finishing_drop(self.bot.observer.parse(self.o),self.config)

    def test_requires_own_banked_progress_and_free_ring(self):
        self.assertIs(self.finishable(),self.drop)
        self.drop['holder']=None
        self.assertIsNone(self.finishable())
        self.drop['holder']=self.me['id']
        self.drop['progress']=.6
        self.assertIsNone(self.finishable())
        self.drop['progress']=2.9
        self.enemy['pos'][0]=-18
        self.assertIsNone(self.finishable())

    def test_zone_or_beam_warning_releases_capture(self):
        self.enemy['charging']=True
        self.assertIsNone(self.finishable())
        self.enemy['charging']=False
        self.me['in_zone']=False
        self.assertIsNone(self.finishable())

    def completes(self, hp, velocity):
        self.me.update(hp=hp,vel=[velocity,0,0])
        for _ in range(12):
            a=self.bot.act(self.o)
            speed=self.me['stats']['boost_speed' if a['boost'] else 'walk_speed']
            for _ in range(2):
                change=[a['move'][k]*speed-self.me['vel'][k] for k in (0,1)]
                fraction=min(1.,self.me['stats']['ground_accel']*.05/max(1e-8,math.hypot(*change)))
                for k in (0,1):
                    self.me['vel'][k]+=change[k]*fraction
                    self.me['pos'][k]+=.05*self.me['vel'][k]
                if math.hypot(*self.me['pos'][:2])>self.drop['radius']:
                    return False
            self.o['t']+=.1
            self.drop['progress']+=.1
            if self.drop['progress']+1e-6>=self.drop['capture_s']:
                return True
        return False

    def test_preserves_nearly_finished_capture_in_motion(self):
        for hp in (500,850,1250):
            for velocity in (0,5):
                with self.subTest(hp=hp,velocity=velocity):
                    self.setUp()
                    self.assertTrue(self.completes(hp,velocity))
