"""[CODEX_ENHANCEMENT_2026-11-21] Bounded local movement with hazard scoring."""
import math


class Navigator:
    def __init__(self, world):
        self.world = world
        self.previous = (0, 0)
        self.anchor = None
        self.anchor_t = 0
        self.escape_until = 0
        self.side = 1

    def move(self, s, goal, mode):
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
        # [ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
        # The inner-circle goal follows our current position. Holding it during
        # an exposed duel otherwise makes every moving candidate lose progress.
        lateral_axis = None
        if distance < .01 and mode == 'balanced' and len(s.enemies) == 1 and not s.urgent:
            enemy = s.enemies[0]
            ep = enemy['pos']
            dx, dy = pos[0] - ep[0], pos[1] - ep[1]
            separation = math.hypot(dx, dy)
            gun = next((w for w in me['weapons'] if w and w['kind'] == 'gun'), None)
            capturing = any(drop['lands_in'] <= 0 and math.dist(pos[:2], drop['pos'][:2]) <= drop['radius']
                            for drop in o.get('drops', []))
            if gun and 1 < separation < gun['stats']['range'] and not capturing:
                scale = 1 + .05*enemy.get('cubes',0)
                if self.world.clear([ep[0],ep[1],ep[2]+7*scale],
                                    [pos[0],pos[1],pos[2]+stats['height']*.5]):
                    lateral_axis = (-dy/separation, dx/separation)
        best, best_score = (0., 0.), -float('inf')
        # Limit detailed collision checks to the nearest projectiles.
        bullets = sorted(o.get('projectiles', []), key=lambda p:math.dist(p['pos'],pos))[:16]
        for dx, dy in candidates:
            end = [pos[0]+dx*look, pos[1]+dy*look, pos[2]]
            if (dx or dy) and not self.world.walkable(pos, end, stats):
                continue
            progress = distance-math.dist(end[:2], goal)
            score = progress*(4 if s.urgent else 1)
            if lateral_axis is not None:
                # Both tangents are legal. Existing obstacle, hazard, zone and
                # momentum scores choose the feasible side and maintain it.
                score += 2*look*abs(dx*lateral_axis[0]+dy*lateral_axis[1])
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
                score += (min(desired,after)-min(desired,before))*(2.5 if mode == 'conservative' else .8)
                # Use cover when retreating. Ray queries only for nearby threats.
                if mode == 'conservative' and before < 160:
                    if not self.world.clear([ep[0],ep[1],ep[2]+7], [end[0],end[1],end[2]+4.5]):
                        score += 8
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
        boost = bool(me['energy'] > 30 and (s.urgent or (mode == 'conservative' and s.enemies)))
        # Do not spend energy or create footstep sounds while already at a quiet goal.
        if distance < 2 and not s.enemies and not s.urgent:
            best, boost = (0., 0.), False
        return list(best), boost
