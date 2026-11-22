"""[CHATGPT_ENHANCEMENT_2026-11-22] Safe detours for observed resource goals, not simulated match scores."""
import math
import unittest
from types import SimpleNamespace
from agent.zone_route import ZoneRoute


class SafeResourceDetourTests(unittest.TestCase):
    def setUp(self):
        self.calls = 0
        self.world = SimpleNamespace(ground=lambda x,y: 0, walkable=self.walkable)
        self.route = ZoneRoute(self.world)
        self.s = SimpleNamespace(urgent=False, health=1.0, enemies=[],
            me=dict(pos=[0.,0.,0.], grounded=True, in_zone=True, stats=dict(step_up=1.2)),
            obs=dict(t=0., zone=dict(center=[0.,0.], radius=100.,
                next_center=[0.,0.], next_radius=90.)))

    def walkable(self, start, end, stats):
        self.calls += 1
        for i in range(21):
            x,y = (start[k] + (end[k]-start[k])*i/20 for k in (0,1))
            if 8 <= x <= 19 and abs(y) < 11:
                return False
        return True

    def test_safe_observed_resource_detours_around_wall(self):
        target = [48.,0.]
        detour = False
        for i in range(100):
            self.s.obs['t'] = i*.1
            self.calls = 0
            tip = self.route.waypoint(self.s, target, resource=True)
            self.assertLessEqual(self.calls,29)
            if abs(tip[1]) > 2:
                detour = True
            pos = self.s.me['pos']
            fraction = min(1,4/max(.001,math.dist(tip,pos[:2])))
            step = [pos[k]+fraction*(tip[k]-pos[k]) for k in (0,1)]
            if self.walkable(pos,step,{}):
                self.s.me['pos'] = [*step,0.]
            if math.dist(target, self.s.me['pos'][:2]) < 4:
                break
        self.assertTrue(detour)
        self.assertLess(math.dist(target,self.s.me['pos'][:2]),4)

    def test_ordinary_quiet_goal_is_not_replanned(self):
        target = [48.,0.]
        self.assertIs(self.route.waypoint(self.s, target),target)
        self.assertEqual(self.calls,0)

    def test_visible_opponent_and_low_health_disable_detour(self):
        target = [48.,0.]
        self.s.enemies = [dict(id=5)]
        self.assertIs(self.route.waypoint(self.s,target,resource=True),target)
        self.s.enemies = []
        self.s.health = .7
        self.assertIs(self.route.waypoint(self.s,target,resource=True),target)
        self.assertEqual(self.calls,0)

    def test_urgent_and_unsafe_future_circle_disable_resource_mode(self):
        target=[48.,0.]
        self.s.obs['zone']['next_radius']=40.
        self.assertIs(self.route.waypoint(self.s,target,resource=True),target)
        self.assertEqual(self.calls,0)
        self.s.obs['zone']['next_radius']=90.
        self.s.me['grounded']=False
        self.assertIs(self.route.waypoint(self.s,target,resource=True),target)
        self.assertEqual(self.calls,0)


if __name__ == '__main__':
    unittest.main()
