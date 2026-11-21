"""[ASTRA_ENHANCEMENT_2026-11-21] Ground route planning within a short decision budget."""
import math
import unittest
from types import SimpleNamespace
from agent.zone_route import ZoneRoute
from agent.world import indexed_inside, index_ring, inside


class ZoneRouteTests(unittest.TestCase):
    def setUp(self):
        self.calls = 0
        self.route = ZoneRoute(SimpleNamespace(ground=lambda x,y: 0,walkable=self.walkable))
        self.s = SimpleNamespace(urgent=True,me=dict(pos=[0,0,0],grounded=True,stats=dict(step_up=1.2)),
                                 obs=dict(t=0,zone=dict(next_center=[48,0],next_radius=9)))

    def walkable(self, start, end, stats):
        self.calls += 1
        for i in range(21):
            x,y = [start[k]+(end[k]-start[k])*i/20 for k in range(2)]
            if 8 <= x <= 19 and abs(y) < 11:
                return False
        return True

    def test_detour_reaches_circle_without_crossing_wall(self):
        target = [48,0]
        for i in range(100):
            self.s.obs['t'] = i*.1
            self.calls = 0
            tip = self.route.waypoint(self.s,target)
            self.assertLessEqual(self.calls,29)
            pos = self.s.me['pos']
            fraction = min(1,4/max(.001,math.dist(tip,pos[:2])))
            move = [pos[k]+fraction*(tip[k]-pos[k]) for k in range(2)]
            if self.walkable(pos,move,{}):
                self.s.me['pos'] = [*move,0]
            if math.dist(target,self.s.me['pos'][:2]) < 4:
                break
        self.assertLess(math.dist(target,self.s.me['pos'][:2]),4)

    def test_normal_goals_and_rooftops_pass_through(self):
        goal = [48,0]
        self.s.urgent = False
        self.assertIs(self.route.waypoint(self.s,goal),goal)
        self.s.urgent = True
        self.s.me['pos'][2] = 12
        self.assertIs(self.route.waypoint(self.s,goal),goal)
        self.assertEqual(self.calls,0)

    def test_indexed_geometry_matches_concave_polygon_including_edges(self):
        ring = [-5,-7,5,-7,2,-1,6,6,0,3,-4,6]
        index = index_ring(ring)
        for y in range(-9,10):
            for x in range(-7,8):
                self.assertEqual(indexed_inside(x,y,index),inside(x,y,ring))
