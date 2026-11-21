"""[ASTRA_ENHANCEMENT_2026-11-21] Idle zone positions during an exposed duel."""
from types import SimpleNamespace
import unittest
from test_agent import recording
from agent.navigation import Navigator
from agent.observation import Observer


class DuelPositionTests(unittest.TestCase):
    def setUp(self):
        _, frames = recording()
        self.obs = frames[0]
        self.obs['self'].update(pos=[0,0,0], in_zone=True, hp=1400)
        self.obs.update(t=10, projectiles=[], drops=[], mechs=[
            dict(id=7,kind='mech',pos=[95,0,0],hp=1400,aim=[3.14,0],weapons=['gun'])])
        self.obs['zone'].update(center=[0,0], next_center=[0,0], radius=300, next_radius=200)
        self.world = SimpleNamespace(walkable=lambda *_: True, clear=lambda *_: True)
        self.nav = Navigator(self.world)

    def move(self, goal=(0.,0.)):
        return self.nav.move(Observer().parse(self.obs),goal,'balanced')[0]

    def test_strafe_free_side_and_continue_in_the_same_direction(self):
        self.world.walkable = lambda start,end,stats: end[1] < 0
        first = self.move()
        self.assertLess(first[1],-.9)
        self.world.walkable = lambda *_: True
        self.assertLess(self.move()[1],-.9)

    def test_hold_cover_or_supply_ring(self):
        self.world.clear = lambda *_: False
        self.assertEqual(self.move(),[0.,0.])
        self.world.clear = lambda *_: True
        self.obs['drops'] = [dict(lands_in=0,radius=8,pos=[0,0,0])]
        self.assertEqual(self.move(),[0.,0.])

    def test_existing_route_takes_precedence(self):
        self.assertGreater(self.move(goal=(-30,0))[0]*-1,.9)
