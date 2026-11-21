"""[ASTRA_ENHANCEMENT_2026-11-21] Movement under visible game projectiles at a quiet goal."""
import unittest
from types import SimpleNamespace
from agent.navigation import Navigator, imminent_crossings
from agent.observation import Observer
from test_agent import recording


class CrossingTests(unittest.TestCase):
    def setUp(self):
        _, stream = recording()
        self.o = stream[0]
        self.me = self.o['self']
        self.me.update(pos=[0,0,0],vel=[0,0,0],grounded=True,in_zone=True)
        self.o.update(t=10,mechs=[],events=[],projectiles=[],drops=[])
        self.o['zone'].update(center=[0,0],next_center=[0,0],radius=200,next_radius=160,shrink_end=110)
        self.nav = Navigator(SimpleNamespace(walkable=lambda *_: True))
        self.shot = dict(id=123,kind='gun',pos=[-100,0,4],vel=[252,0,0])
        self.o['projectiles'] = [self.shot]

    def action(self):
        return self.nav.move(Observer().parse(self.o),[0,0],'balanced')

    def test_incoming_projectile_at_quiet_goal_gets_a_lateral_move(self):
        move, boost = self.action()
        self.assertGreater(abs(move[1]),.9)
        self.assertFalse(boost)

    def test_existing_lateral_velocity_matters_to_the_crossing(self):
        self.shot['pos'][1] = 5
        self.assertFalse(imminent_crossings(self.me,[self.shot]))
        self.me['vel'][1] = self.me['stats']['walk_speed']
        self.assertIn(123, imminent_crossings(self.me,[self.shot]))

    def test_harmless_shots_do_not_disturb_quiet_goal(self):
        self.shot['vel'][0] = -252
        self.assertEqual(self.action()[0],[0.,0.])
        self.shot.update(vel=[252,0,0],pos=[-100,0,20])
        self.assertEqual(self.action()[0],[0.,0.])
