"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Plan a ground detour when an urgent trip into the safe circle meets a wall.
"""
import heapq
import math


class ZoneRoute:
    spacing = 8
    offsets = ((1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(-1,-1),(1,-1))

    def __init__(self, world):
        self.world = world
        self.clear()

    def clear(self):
        self.anchor = None
        self.path = []
        self.frontier = []
        self.retry_at = 0
        self.restrict = None  # [CHATGPT_ENHANCEMENT_2026-11-22] Optional safe-circle bounds for loot paths.

    def point(self, cell):
        x = self.anchor[0] + self.spacing*cell[0]
        y = self.anchor[1] + self.spacing*cell[1]
        return [x,y,self.world.ground(x,y)]

    def start(self, pos, goal):
        self.anchor = pos[:]
        self.goal = goal[:]
        self.parent = {(0,0): None}
        self.cost = {(0,0): 0}
        self.frontier = [(math.dist(pos[:2],goal),0,(0,0))]
        self.path = []

    def expand(self, stats):
        """[CHATGPT_ENHANCEMENT_2026-11-22] Keep optional resource routes inside both safe circles."""
        # Bound geometry queries per decision. Resume the same search on the next observation.
        for _ in range(3):
            if not self.frontier or len(self.cost) >= 420:
                self.frontier.clear()
                return
            _,cost,cell = heapq.heappop(self.frontier)
            if cost != self.cost[cell]:
                continue
            src = self.point(cell)
            remaining = math.dist(src[:2],self.goal)
            gain = math.dist(self.anchor[:2],self.goal)-remaining
            # For a long trip, solve the local obstruction before planning the next leg.
            if remaining <= 20 or gain >= 48:
                fraction = min(16/max(remaining,1e-9),1.)
                out = [src[k]+fraction*(self.goal[k]-src[k]) for k in range(2)]
                if self.world.walkable(src,out,stats):
                    self.path = [out]
                    while self.parent[cell] is not None:
                        self.path.append(self.point(cell)[:2])
                        cell = self.parent[cell]
                    self.path.reverse()
                    self.frontier.clear()
                    return
            for dx,dy in self.offsets:
                other = cell[0]+dx,cell[1]+dy
                total = cost + self.spacing*math.hypot(dx,dy)
                if total >= self.cost.get(other,math.inf):
                    continue
                dest = self.point(other)
                if self.restrict and any(math.dist(dest[:2],center) > radius
                                         for center,radius in self.restrict):
                    continue
                if self.world.walkable(src,dest,stats):
                    self.cost[other],self.parent[other] = total,cell
                    heapq.heappush(self.frontier,(total+math.dist(dest[:2],self.goal),total,other))

    def waypoint(self, s, goal, resource=False):
        """[CHATGPT_ENHANCEMENT_2026-11-22] Incrementally detour around buildings for safe visible loot.

        Legacy urgent-zone routing is unchanged. Resource detours are separately
        instantiated by the policy, are disabled around visible opponents, damage
        reserves or zone urgency, and cannot plan outside either safe circle.
        They never invent an item position or override a finishable capture.
        """
        me, zone = s.me, s.obs['zone']
        pos, stats = me['pos'], me['stats']
        circles = None
        resource_safe = (resource and not s.urgent and not s.enemies and
                         s.health >= .80 and me['grounded'] and me['in_zone'])
        if resource_safe:
            circles = ((zone['center'], zone['radius']-14),
                       (zone['next_center'], zone['next_radius']-14))
            if any(radius <= 18 or math.dist(pos[:2], center) >= radius or
                   math.dist(goal, center) >= radius for center,radius in circles):
                resource_safe = False
        if (not (s.urgent or resource_safe) or not me['grounded'] or
                (not resource_safe and
                 math.dist(pos[:2], zone['next_center']) < zone['next_radius']-5) or
                abs(pos[2]-self.world.ground(*pos[:2])) > stats['step_up']):
            self.clear()
            return goal
        self.restrict = circles if resource_safe else None
        if self.anchor is not None and math.dist(self.goal, goal) > 18:
            self.clear()
            self.restrict = circles if resource_safe else None
        if self.path:
            while self.path and math.dist(pos[:2], self.path[0]) < 3:
                self.path.pop(0)
            for i in range(min(len(self.path),4)-1,-1,-1):
                if self.world.walkable(pos,self.path[i],stats):
                    self.path = self.path[i:]
                    return self.path[0]
            self.clear()
            self.restrict = circles if resource_safe else None
        if not self.frontier:
            distance = math.dist(pos[:2],goal)
            if distance < 8 or s.obs['t'] < self.retry_at:
                return goal
            fraction = min(16/distance,1.)
            ahead = [pos[k]+fraction*(goal[k]-pos[k]) for k in range(2)]
            if self.world.walkable(pos,ahead,stats):
                return goal
            self.start(pos,goal)
        self.expand(stats)
        if self.path:
            return self.path[0]
        if not self.frontier:
            self.retry_at = s.obs['t']+1
        return goal
