"""[ASTRA_ENHANCEMENT_2026-11-21] Pick up a second weapon on an early inward route."""
import unittest
from test_agent import recording
from agent.observation import Observer
from agent.strategy import Strategy


class ArmingRouteTests(unittest.TestCase):
    def setUp(self):
        _, observations = recording()
        self.o = observations[0]
        self.o.update(t=5, mechs=[], pickups=[], cubes=[], drops=[])
        self.o['self'].update(pos=[180,0,0], in_zone=True)
        self.o['self']['weapons'][1] = None
        self.o['zone'].update(center=[0,0], next_center=[0,0], radius=350, next_radius=100,
                              shrink_start=55, shrink_end=100)
        self.item = dict(id=8001, kind='laser', pos=[125,20,0])
        self.o['pickups'] = [self.item]
        self.strategy = Strategy()

    def goal(self):
        return self.strategy.goal(Observer().parse(self.o), 'balanced')

    def test_inward_pickup_persists_when_torso_turns(self):
        self.assertEqual(self.goal(), [125,20])
        self.o['pickups'] = []
        self.o['t'] += 2
        self.assertEqual(self.goal(), [125,20])
        self.o['t'] += 15
        self.assertNotEqual(self.goal(), [125,20])

    def test_approach_aborted_for_clock_or_contestation(self):
        self.assertEqual(self.goal(), [125,20])
        self.o['mechs'] = [dict(kind='mech', id=4, pos=[125,25,0])]
        self.assertNotEqual(self.goal(), [125,20])
        self.o.update(mechs=[], t=48)
        self.assertNotEqual(self.goal(), [125,20])

    def test_reject_outward_detour_and_keep_inner_resources_first(self):
        self.item['pos'] = [200,0,0]
        self.assertNotEqual(self.goal(), [200,0])
        self.item['pos'] = [125,20,0]
        self.o['cubes'] = [dict(id=5000,pos=[80,0,0])]
        self.assertEqual(self.goal(), [80,0])
