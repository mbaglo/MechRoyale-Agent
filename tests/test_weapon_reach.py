"""[CODEX_ENHANCEMENT_2026-11-21] EXP-004 isolated weapon-goal regressions."""
import copy
import unittest
from test_agent import recording
from agent.observation import Observer
from agent.strategy import Strategy


class WeaponReachTests(unittest.TestCase):
    def setUp(self):
        _,observations = recording()
        self.o = copy.deepcopy(observations[0])
        self.o.update(t=10,mechs=[],events=[],sounds=[],projectiles=[],cubes=[],crates=[],drops=[])
        self.o['self'].update(pos=[0,0,0],hp=1400,max_hp=1400,in_zone=True)
        self.o['self']['weapons'][1] = None
        self.o['zone'] = dict(center=[0,0],radius=500,next_center=[0,0],next_radius=300,shrink_start=60,shrink_end=110,dps=20)
        self.o['pickups'] = [dict(id=8001,kind='laser',pos=[100,0,0])]

    def goal(self):
        return Strategy().goal(Observer().parse(self.o),'balanced')

    def test_safe_weapon_beyond_old_radius_is_goal(self):
        self.assertEqual(self.goal(),[100,0])

    def test_search_is_bounded(self):
        self.o['pickups'][0]['pos'][0] = 135
        self.assertEqual(self.goal(),[0,0])

    def test_contested_weapon_is_not_goal(self):
        self.o['mechs'] = [dict(id=5,kind='mech',pos=[110,0,0],vel=[0,0,0],aim=[0,0])]
        self.assertEqual(self.goal(),[0,0])

    def test_urgent_zone_takes_priority(self):
        self.o['self']['in_zone'] = False
        self.assertEqual(self.goal(),[0,0])

    def test_roof_and_outside_future_zone_are_rejected(self):
        self.o['pickups'][0]['pos'][2] = 8
        self.assertEqual(self.goal(),[0,0])
        self.o['pickups'][0]['pos'][2] = 0
        self.o['zone']['next_radius'] = 90
        self.assertEqual(self.goal(),[0,0])

    def test_duplicate_weapon_and_full_inventory_are_rejected(self):
        self.o['pickups'][0]['kind'] = 'gun'
        self.assertEqual(self.goal(),[0,0])
        self.o['pickups'][0]['kind'] = 'laser'
        self.o['self']['weapons'][1] = dict(kind='mortar')
        self.assertEqual(self.goal(),[0,0])


if __name__=='__main__':
    unittest.main()
