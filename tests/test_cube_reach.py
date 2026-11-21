"""[CODEX_ENHANCEMENT_2026-11-21] EXP-010 safe drop collection regressions."""
import copy
import unittest
from test_agent import recording
from agent.observation import Observer
from agent.strategy import Strategy


class CubeReachTests(unittest.TestCase):
    def setUp(self):
        _,obs=recording();self.o=copy.deepcopy(obs[0])
        self.o.update(t=10,mechs=[],events=[],sounds=[],projectiles=[],pickups=[],crates=[],drops=[])
        self.o['self'].update(pos=[0,0,0],hp=1400,max_hp=1400,in_zone=True)
        self.o['zone']=dict(center=[0,0],radius=500,next_center=[0,0],next_radius=300,shrink_start=60,shrink_end=110,dps=20)
        self.o['cubes']=[dict(id=5001,pos=[75,0,0]),dict(id=5002,pos=[76,0,0])]

    def goal(self):return Strategy().goal(Observer().parse(self.o),'balanced')

    def test_safe_drops_at_typical_combat_distance_are_pursued(self):
        self.assertEqual(self.goal(),[75,0])

    def test_cube_pursuit_is_bounded(self):
        self.o['cubes']=[dict(id=5001,pos=[135,0,0])]
        self.assertEqual(self.goal(),[0,0])

    def test_contested_drop_is_avoided(self):
        self.o['mechs']=[dict(id=5,kind='mech',pos=[100,0,0],vel=[0,0,0],aim=[0,0],hp=1400)]
        self.assertEqual(self.goal(),[0,0])

    def test_zone_urgency_overrides_drop_collection(self):
        self.o['self']['in_zone']=False
        self.assertEqual(self.goal(),[0,0])

    def test_future_zone_and_vertical_filters_are_retained(self):
        self.o['zone']['next_radius']=70
        self.assertEqual(self.goal(),[0,0])
        self.o['zone']['next_radius']=300
        for c in self.o['cubes']:c['pos'][2]=5
        self.assertEqual(self.goal(),[0,0])

    def test_nearer_safe_resource_still_wins(self):
        self.o['cubes'].append(dict(id=5003,pos=[10,0,0]))
        self.assertEqual(self.goal(),[10,0])


if __name__=='__main__':unittest.main()
