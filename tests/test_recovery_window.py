"""[ASTRA_ENHANCEMENT_2026-11-21] Verify disengagement only during a real healing opportunity."""
import math
import unittest
from test_agent import recording
from agent.policy import Bot


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        h, stream = recording()
        self.o = stream[0]
        self.bot = Bot(h)
        self.bot.world.clear = lambda *_: True
        self.bot.world.walkable = lambda *_: True
        self.o.update(t=10,projectiles=[],crates=[],drops=[],pickups=[],cubes=[],sounds=[],
                      events=[dict(type='damaged',amount=45,weapon='gun',by=5,bearing=0)])
        self.me = self.o['self']
        self.me.update(pos=[0,0,0],aim=[0,math.atan2(-2.5,140)],in_zone=True,hp=650)
        self.me['weapons'][0].update(ammo=12,cooldown=0,reload=0)
        self.o['mechs'] = [dict(id=5,kind='mech',hp=1400,pos=[140,0,0],vel=[0,0,0],aim=[0,0])]
        self.o['zone'].update(center=[0,0],next_center=[0,0],radius=400,next_radius=300,shrink_end=120)

    def test_stop_at_quiet_window_and_resume_immediately_when_hit(self):
        self.assertTrue(self.bot.act(self.o)['fire'][0])
        self.o.update(t=15, events=[])
        self.assertFalse(self.bot.act(self.o)['fire'][0])
        self.o.update(t=15.1, events=[dict(type='damaged',amount=45,weapon='gun',by=5,bearing=0)])
        self.assertTrue(self.bot.act(self.o)['fire'][0])

    def test_outgoing_damage_and_zone_restart_the_clock(self):
        self.bot.act(self.o)
        self.o.update(t=14.9, events=[dict(type='hit',target=5,amount=45,weapon='gun')])
        self.assertTrue(self.bot.act(self.o)['fire'][0])
        self.o.update(t=17,events=[])
        self.assertTrue(self.bot.act(self.o)['fire'][0])
        self.me['in_zone'] = False
        self.o['t'] = 23
        self.bot.act(self.o)
        self.me['in_zone'] = True
        self.o['t'] += 6  # First in-zone observation after a gap starts a fresh clock.
        self.assertTrue(self.bot.act(self.o)['fire'][0])

    def test_regenerating_mech_can_finish_opponent_or_answer_laser(self):
        self.bot.act(self.o)
        self.o.update(t=16, events=[])
        self.o['mechs'][0]['hp'] = 40
        self.assertTrue(self.bot.act(self.o)['fire'][0])
        self.o['mechs'][0].update(hp=1400,charging=True)
        self.assertTrue(self.bot.act(self.o)['fire'][0])
