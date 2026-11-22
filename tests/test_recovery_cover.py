"""[ASTRA_ENHANCEMENT_2026-11-21] [CHATGPT_ENHANCEMENT_2026-11-21] Verify shelter, release on contact and zone priority."""
from types import SimpleNamespace
import unittest
from test_agent import recording
from agent.observation import Observer
from agent.recovery_cover import RecoveryCover


class RecoveryCoverTests(unittest.TestCase):
    def setUp(self):
        hello, frames = recording()
        self.o = frames[0]
        self.o.update(t=10, mechs=[dict(id=5,kind='mech',pos=[-135,0,0])],
                      projectiles=[], events=[], drops=[])
        self.me = self.o['self']
        self.me.update(pos=[0,0,0],grounded=True,in_zone=True,hp=650)
        self.o['zone'].update(center=[0,0],radius=300,next_center=[0,0],next_radius=200,shrink_end=120)
        self.observer = Observer()
        self.observer.parse(self.o)
        self.o['t'] += 6
        world = SimpleNamespace(ground=lambda *_: 0, clear=lambda a,b: b[1] < 5, walkable=lambda *_: True)
        self.cover = RecoveryCover(world,hello['config'])

    def route(self):
        return self.cover.route(self.observer.parse(self.o))

    def test_find_shelter_then_hold_until_window_breaks(self):
        goal, hold = self.route()
        self.assertAlmostEqual(goal[1],6)
        self.assertFalse(hold)
        self.me['pos'] = [0,6,0]
        self.assertEqual(self.route(),(None,True))
        self.o['events'] = [dict(type='damaged',amount=45,weapon='gun',by=5,bearing=0)]
        self.assertEqual(self.route(),(None,False))

    def test_unseen_pursuer_only_extends_existing_shelter_briefly(self):
        self.me['pos'] = [0,6,0]
        self.route()
        self.o['mechs'] = []
        self.o['t'] += 1
        self.assertEqual(self.route(),(None,True))
        self.o['t'] += 2
        self.assertEqual(self.route(),(None,False))

    def test_reject_unsafe_zone_or_unwalkable_route(self):
        self.cover.world.walkable = lambda *_: False
        self.assertEqual(self.route(),(None,False))
        self.me['in_zone'] = False
        self.me['pos'] = [0,6,0]
        self.assertEqual(self.route(),(None,False))
