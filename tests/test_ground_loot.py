"""[ASTRA_FIX_2026-11-21] Ground elevation, collection height and blocked routes."""
import unittest
from types import SimpleNamespace

from agent.observation import Observer
from agent.policy import Bot
from agent.strategy import Strategy
from test_agent import recording


class GroundLootTests(unittest.TestCase):
    def setUp(self):
        h,frames=recording()
        self.bot=Bot(h)
        self.o=frames[0]
        for key in ('mechs','cubes','crates','drops','events','sounds','projectiles','pickups'):
            self.o[key]=[]
        self.o['self'].update(pos=[284.43,-231.63,1.8],grounded=True,in_zone=True)
        self.o.update(t=10,zone=dict(center=[284.43,-231.63],next_center=[284.43,-231.63],
                                     radius=350,next_radius=250,shrink_start=60,shrink_end=110))
        self.item=dict(id=8003,kind='laser',pos=[222.99,-257.34,-3.1])
        self.o['pickups']=[self.item]

    def goal(self):
        return self.bot.strategy.goal(self.bot.observer.parse(self.o),'balanced')

    def test_walkable_ground_goal_and_unchanged_take_radius(self):
        self.assertEqual(self.goal(),self.item['pos'][:2])
        self.assertNotIn('take',self.bot.act(self.o))
        self.o['self']['pos']=self.item['pos'][:]
        self.assertEqual(self.bot.act(self.o)['take'],self.item['id'])

    def test_rooftop_and_unwalkable_ground_fall_back(self):
        self.item['pos'][2]+=16
        self.assertEqual(self.goal(),self.o['self']['pos'][:2])
        self.item['pos'][2]-=16
        self.bot.world.walkable=lambda *_:False
        self.assertEqual(self.goal(),self.o['self']['pos'][:2])

    def test_bounded_extra_checks_preserve_existing_flat_option(self):
        o=self.o
        o['self']['pos']=[0,0,0]
        o['zone'].update(center=[0,0],next_center=[0,0])
        o['pickups']=[dict(id=8000+i,kind='laser',pos=[d,0,6 if i<3 else 0])
                      for i,d in enumerate((20,25,30,40))]
        checks=[]
        world=SimpleNamespace(ground=lambda x,y:6 if x>0 else 0,
                              walkable=lambda p,q,s:checks.append(q) or False)
        goal=Strategy(world).goal(Observer().parse(o),'balanced')
        self.assertEqual(goal,[40,0])
        self.assertEqual(len(checks),2)
