"""[CODEX_ENHANCEMENT_2026-11-21] Incremental, node-bounded ground A*."""
import heapq
import math
from .tuning import DEFAULT


class Router:
    def __init__(self, world, tuning=DEFAULT):
        self.world, self.tuning = world, tuning
        self.goal = None
        self.origin = None
        self.path = []
        self.frontier = []
        self.cost = {}
        self.parents = {}
        self.closed = set()
        self.edges = {}
        self.started = -100
        self.expansions = 0
        self.shape = None

    def point(self, node):
        x = self.origin[0]+node[0]*self.tuning.route_step
        y = self.origin[1]+node[1]*self.tuning.route_step
        return [x,y,self.world.ground(x,y)]

    def start(self, pos, goal, t, stats):
        self.origin, self.goal, self.started = pos[:],list(goal),t
        self.path, self.parents, self.closed, self.edges = [],{},set(),{}
        self.frontier, self.cost = [(math.dist(pos[:2],goal),0.,(0,0))],{(0,0):0.}
        self.shape = (stats.get('radius',2.5),stats.get('height',9),stats.get('step_up',1.2),stats.get('max_slope_deg',50))
        self.expansions = 0

    def waypoint(self, s, goal):
        pos,stats = s.me['pos'],s.me['stats']
        # Rooftop/airborne motion retains the proven local planner.
        if not s.me.get('grounded',True) or pos[2]-self.world.ground(*pos[:2]) > stats.get('step_up',1.2)+1:
            return goal
        if math.dist(pos[:2],goal) < 12:
            return goal
        shape = (stats.get('radius',2.5),stats.get('height',9),stats.get('step_up',1.2),stats.get('max_slope_deg',50))
        if (self.goal is None or math.dist(goal,self.goal)>15 or s.obs['t']-self.started>8 or shape != self.shape):
            self.start(pos,goal,s.obs['t'],stats)
        for _ in range(self.tuning.route_expansions_per_tick):
            if self.path or not self.frontier or len(self.closed)>=self.tuning.route_max_nodes:
                break
            _,cost,node = heapq.heappop(self.frontier)
            if node in self.closed:
                continue
            self.closed.add(node)
            self.expansions += 1
            point = self.point(node)
            distance = math.dist(point[:2],self.goal)
            # A short verified final link, not merely a nearby point behind a wall.
            end = [*self.goal,self.world.ground(*self.goal)]
            if distance <= self.tuning.route_step*1.5 and self.world.walkable(point,end,stats):
                path = [end]
                while node != (0,0):
                    path.append(self.point(node))
                    node = self.parents[node]
                self.path = list(reversed(path))
                break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nxt = (node[0]+dx,node[1]+dy)
                if nxt in self.closed or math.hypot(*nxt)*self.tuning.route_step > self.tuning.route_radius:
                    continue
                target = self.point(nxt)
                key = (node,nxt)
                if key not in self.edges:
                    self.edges[key] = self.world.walkable(point,target,stats)
                if not self.edges[key]:
                    continue
                cost2 = cost+self.tuning.route_step+abs(target[2]-point[2])*.5
                if cost2 < self.cost.get(nxt,float('inf')):
                    self.cost[nxt],self.parents[nxt] = cost2,node
                    heapq.heappush(self.frontier,(cost2+math.dist(target[:2],self.goal),cost2,nxt))
        while self.path and math.dist(pos[:2],self.path[0][:2]) < 4:
            self.path.pop(0)
        if self.path:
            # Recheck the live connection after displacement/stuck recovery.
            if self.world.walkable(pos,self.path[0],stats):
                return self.path[0][:2]
            self.start(pos,goal,s.obs['t'],stats)
        return goal  # Original 16-direction planner remains the fallback.
