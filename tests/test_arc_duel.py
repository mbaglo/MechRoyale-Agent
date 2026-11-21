"""[ASTRA_ENHANCEMENT_2026-11-21] Test the in-game lightning versus laser matchup."""
import math
import unittest
from test_agent import recording
from agent.policy import Bot


class ArcDuelTests(unittest.TestCase):
    def setUp(self):
        h, frames = recording()
        self.o = frames[0]
        self.bot = Bot(h)
        self.bot.world.walkable = lambda *_: True
        self.bot.world.clear = lambda *_: True
        self.o.update(t=10, mechs=[], projectiles=[], crates=[], cubes=[], drops=[], pickups=[], events=[], sounds=[])
        self.me = self.o['self']
        self.me.update(pos=[0,0,0], in_zone=True, hp=1400, energy=100, aim=[0,0])
        self.me['weapons'][1] = dict(kind='lightning',cooldown=0,stats=h['config']['weapons']['lightning'])
        self.enemy = dict(id=6,kind='mech',pos=[65,0,0],vel=[0,0,0],hp=1400,
                          aim=[math.pi,0],weapons=['gun','laser'])
        self.o['mechs'] = [self.enemy]
        self.o['zone'].update(center=[0,0], next_center=[0,0], radius=300,next_radius=200,shrink_end=110)

    def test_close_gap_then_use_arc_without_spending_energy_on_boost(self):
        first = self.bot.act(self.o)
        self.assertGreater(first['move'][0],.5)
        self.assertTrue(first['boost'])
        self.assertFalse(first['fire'][1])
        self.me['pos'] = [25,0,0]
        second = self.bot.act(self.o)
        self.assertTrue(second['fire'][1])
        self.assertFalse(second['boost'])

    def test_no_rush_with_low_energy_blocked_sight_or_blast_weapon(self):
        self.me['energy'] = 15
        self.assertLessEqual(self.bot.act(self.o)['move'][0],.1)
        self.me['energy'] = 100
        self.bot.world.clear = lambda *_: False
        self.assertLessEqual(self.bot.act(self.o)['move'][0],.1)
        self.bot.world.clear = lambda *_: True
        self.enemy['weapons'] = ['gun','mortar']
        self.assertLessEqual(self.bot.act(self.o)['move'][0],.1)

    def test_crossfire_blocks_approach(self):
        self.o['mechs'].append(dict(self.enemy, id=8,pos=[70,5,0]))
        self.assertLess(self.bot.act(self.o)['move'][0],0)

    def test_capture_takes_priority_over_closing_the_gap(self):
        self.o['drops'] = [dict(id=20000,lands_in=0,pos=[0,0,0],radius=8)]
        self.assertLessEqual(self.bot.act(self.o)['move'][0],.1)
