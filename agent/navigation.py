"""[CODEX_ENHANCEMENT_2026-11-21] Bounded local movement with hazard scoring."""
import math
from .tuning import DEFAULT
from .routing import Router
from .energy import EnergyPolicy


class Navigator:
    def __init__(self, world, tuning=DEFAULT):
        self.world = world
        self.previous = (0, 0)
        self.anchor = None
        self.anchor_t = 0
        self.escape_until = 0
        self.side = 1
        self.router = Router(world,tuning)
        self.energy = EnergyPolicy(tuning)
        self.tuning = tuning
        self.cover_cache = {}

    def move(self, s, goal, mode):
        # [CODEX_ENHANCEMENT_2026-11-21] Incremental route selection feeds
        # the original local candidate planner rather than replacing it.
        goal = self.router.waypoint(s,goal)
        return self.local_move(s,goal,mode)

    def local_move(self, s, goal, mode):
        me, o = s.me, s.obs
        pos, stats = me['pos'], me['stats']
        if self.anchor is None or o['t']-self.anchor_t > 1.5:
            if self.anchor and math.dist(pos[:2], self.anchor[:2]) < 1.5 and math.hypot(*self.previous) > .5:
                self.escape_until = o['t']+2
                self.side = -self.side
            self.anchor, self.anchor_t = pos[:], o['t']
        distance = math.dist(pos[:2], goal)
        base = math.atan2(goal[1]-pos[1], goal[0]-pos[0])
        candidates = [(0., 0.)] + [(math.cos(base+i*math.pi/8), math.sin(base+i*math.pi/8)) for i in range(16)]
        zone = o['zone']
        look = min(8, max(3, distance))
        best, best_score = (0., 0.), -float('inf')
        # Limit detailed collision checks to the nearest projectiles.
        bullets = sorted(o.get('projectiles', []), key=lambda p:math.dist(p['pos'],pos))[:16]
        # [CODEX_ENHANCEMENT_2026-11-21] Cache approximate cover only inside
        # this decision, never across changes in enemy position or geometry.
        self.cover_cache.clear()
        for dx, dy in candidates:
            end = [pos[0]+dx*look, pos[1]+dy*look, pos[2]]
            if (dx or dy) and not self.world.walkable(pos, end, stats):
                continue
            # Penalize one-way pockets; verify a second step in the escape direction.
            if (dx or dy) and s.pressure > .8:
                farther = [pos[0]+dx*look*2,pos[1]+dy*look*2,pos[2]]
                if not self.world.walkable(end,farther,stats):
                    score_dead_end = 7
                else:
                    score_dead_end = 0
            else:
                score_dead_end = 0
            progress = distance-math.dist(end[:2], goal)
            score = progress*(4 if s.urgent else 1)
            score -= score_dead_end
            score += .8*(dx*self.previous[0]+dy*self.previous[1])
            if self.escape_until > o['t']:
                score += 12*self.side*(dx*(-math.sin(base))+dy*math.cos(base))
            outside = max(0, math.dist(end[:2], zone['center'])-zone['radius']+6)
            score -= outside*10
            if s.urgent:
                score -= max(0, math.dist(end[:2], zone['next_center'])-zone['next_radius']+8)*2
            for enemy in s.enemies[:6]:
                ep = enemy['pos']
                before, after = math.dist(pos[:2],ep[:2]), math.dist(end[:2],ep[:2])
                desired = 130 if mode == 'conservative' else 75
                # [CODEX_FIX_2026-11-21] Do not flee equally from stationary
                # observers and coordinated pursuers. Amplify crossfire escape.
                weight = (s.threat_weights or {}).get(enemy['id'],.5)
                score += (min(desired,after)-min(desired,before))*(2.5 if mode == 'conservative' else .8)*min(2,weight+.2)
                # Use cover when retreating. Ray queries only for nearby threats.
                # [CODEX_ENHANCEMENT_2026-11-21] Cover rays for the closest
                # three threats bound cost; all six still affect separation.
                if mode == 'conservative' and before < 160 and enemy in s.enemies[:3]:
                    key = (enemy['id'],round(end[0]/4),round(end[1]/4))
                    if key not in self.cover_cache:
                        self.cover_cache[key] = not self.world.clear([ep[0],ep[1],ep[2]+7], [end[0],end[1],end[2]+4.5])
                    if self.cover_cache[key]:
                        score += 8*min(1,weight)
                if enemy.get('charging') and before < 280:
                    yaw = enemy['aim'][0]
                    lateral = abs((end[0]-ep[0])*math.sin(yaw)-(end[1]-ep[1])*math.cos(yaw))
                    score += min(lateral, 12)*.7
            speed = stats['walk_speed']
            for bullet in bullets:
                rel = [bullet['pos'][k]-pos[k] for k in range(3)]
                vel = [bullet['vel'][0]-dx*speed, bullet['vel'][1]-dy*speed, bullet['vel'][2]]
                vv = sum(v*v for v in vel)
                t = max(0, min(.65, -sum(rel[k]*vel[k] for k in range(3))/max(1,vv)))
                horizontal = math.hypot(rel[0]+vel[0]*t, rel[1]+vel[1]*t)
                height = rel[2]+vel[2]*t
                if -2 < height < stats.get('height',9)+2:
                    score -= max(0, stats.get('radius',2.5)+2-horizontal)*5
            if score > best_score:
                best, best_score = (dx,dy), score
        self.previous = best
        # [CODEX_FIX_2026-11-21] Baseline boost rule is retained here for
        # comparison: energy > 30 and (urgent or conservative with enemies).
        danger = self.projectile_danger(s,best,bullets)
        boost = self.energy.boost(s,best,danger)
        # Do not spend energy or create footstep sounds while already at a quiet goal.
        if distance < 2 and not s.enemies and not s.urgent and not danger:
            best, boost = (0., 0.), False
        return list(best), boost

    def projectile_danger(self, s, move, bullets):
        """[CODEX_ENHANCEMENT_2026-11-21] Boost only from a nearby collision course."""
        pos = s.me['pos']
        for p in bullets:
            rel = [p['pos'][k]-pos[k] for k in range(3)]
            v = p['vel']
            vv = sum(x*x for x in v)
            t = -sum(rel[k]*v[k] for k in range(3))/max(1,vv)
            if 0 < t < .6 and -2 < rel[2]+v[2]*t < s.me['stats'].get('height',9)+2:
                if math.hypot(rel[0]+v[0]*t,rel[1]+v[1]*t) < s.me['stats'].get('radius',2.5)+2:
                    return True
        return False
