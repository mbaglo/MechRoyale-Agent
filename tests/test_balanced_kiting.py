"""[CODEX_ENHANCEMENT_2026-11-21] EXP-005 held-goal kiting regressions."""
import copy
from types import SimpleNamespace
import unittest
from test_agent import recording
from agent.navigation import Navigator
from agent.observation import Observer


class BalancedKitingTests(unittest.TestCase):
    def setUp(self):
        _,observations=recording();self.o=copy.deepcopy(observations[0])
        self.o.update(t=10,projectiles=[],mechs=[],events=[],sounds=[])
        self.o['self'].update(pos=[0,0,0],hp=1400,max_hp=1400,energy=100,in_zone=True)
        self.o['zone']=dict(center=[0,0],radius=500,next_center=[0,0],next_radius=300,shrink_start=60,shrink_end=110,dps=20)
        self.world=SimpleNamespace(walkable=lambda a,b,s:True,clear=lambda a,b:True)

    def enemy(self,x=40,y=0):
        return dict(id=5,kind='mech',pos=[x,y,0],vel=[0,0,0],aim=[0,0],hp=1400,max_hp=1400)

    def move(self,mode='balanced'):
        return Navigator(self.world).move(Observer().parse(self.o),[0,0],mode)[0]

    def test_close_threat_breaks_stationary_goal(self):
        self.o['mechs']=[self.enemy()]
        self.assertLess(self.move()[0],-.7)

    def test_rotated_threat_escapes_in_opposite_direction(self):
        self.o['mechs']=[self.enemy(x=0,y=40)]
        self.assertLess(self.move()[1],-.7)

    def test_distant_enemy_does_not_pull_away_from_goal(self):
        self.o['mechs']=[self.enemy(x=160)]
        self.assertEqual(self.move(),[0.,0.])

    def test_quiet_goal_stays_stationary(self):
        self.assertEqual(self.move(),[0.,0.])

    def test_collision_veto_still_applies(self):
        self.o['mechs']=[self.enemy()]
        self.world.walkable=lambda a,b,s:False
        self.assertEqual(self.move(),[0.,0.])

    def test_aggressive_weight_remains_unchanged(self):
        self.o['mechs']=[self.enemy()]
        self.assertEqual(self.move('aggressive'),[0.,0.])


if __name__=='__main__': unittest.main()
