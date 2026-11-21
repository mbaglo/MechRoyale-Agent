"""[CODEX_ENHANCEMENT_2026-11-21] Placement-first mode transitions and goals."""
import math
from .tuning import DEFAULT


class Strategy:
    def __init__(self, tuning=DEFAULT):
        self.mode = 'balanced'
        self.tuning = tuning
        self.emergency = False

    def choose(self, s):
        close = [e for e in s.enemies if math.dist(e['pos'], s.me['pos']) < 100]
        weak = close and close[0].get('hp', 1400) < s.me['hp']*.5
        self.emergency = s.emergency
        # [CODEX_FIX_2026-11-21] Low enemy HP alone does not justify pursuit.
        ranged = close and any(w and w.get('cooldown',0) < .5 and
                              math.dist(close[0]['pos'],s.me['pos']) < w['stats'].get('range',180)
                              for w in s.me['weapons'])
        favorable = (s.pressure < 1.8 and s.escape_fraction >= .5 and s.me['energy'] >= 40 and
                     not s.urgent and s.me['in_zone'] and ranged)
        if (s.health < .42 or s.pressure >= self.tuning.conservative_pressure or s.pursuing >= 2 or
                s.urgent or s.emergency or (s.phase=='late' and s.pressure>1.2)):
            self.mode = 'conservative'
        elif s.health > .72 and weak and len(close) == 1 and favorable:
            self.mode = 'aggressive'
        elif s.health > .55 or self.mode != 'conservative':
            self.mode = 'balanced'
        return self.mode

    def goal(self, s, mode):
        o, me = s.obs, s.me
        pos = me['pos']
        z = o['zone']
        center = z['next_center']
        radius = max(0, z['next_radius']-20)
        d = math.dist(pos[:2], center)
        # Remain on the quieter side of the next circle, leaving escape space.
        fraction = min(1, radius*.55/max(d, 1))
        goal = [center[k]+(pos[k]-center[k])*fraction for k in range(2)]
        # [CODEX_ENHANCEMENT_2026-11-21] Retreat toward the least pressured
        # reachable sector of the future circle, rather than into its busy center.
        if s.pressure > .8 and s.enemies and not s.urgent:
            weights = s.threat_weights or {}
            vx = sum((pos[0]-e['pos'][0])/max(1,math.dist(pos[:2],e['pos'][:2]))*weights.get(e['id'],.2) for e in s.enemies)
            vy = sum((pos[1]-e['pos'][1])/max(1,math.dist(pos[:2],e['pos'][:2]))*weights.get(e['id'],.2) for e in s.enemies)
            length = math.hypot(vx,vy)
            if length > .1:
                goal = [pos[0]+vx/length*55,pos[1]+vy/length*55]
                offset = math.dist(goal,center)
                if offset > radius and offset > 0:
                    goal = [center[k]+(goal[k]-center[k])*radius/offset for k in range(2)]
        if s.urgent:
            return goal
        if s.emergency or s.pressure >= self.tuning.conservative_pressure:
            return goal
        candidates = []
        for p in o.get('cubes', []):
            # [CODEX_ENHANCEMENT_2026-11-21] Late loot detours stay short;
            # early weapon/resource acquisition keeps the baseline reach.
            candidates.append((p, 1.0, 25 if s.phase=='late' else 55))
        if any(w is None for w in me['weapons']):
            for p in o.get('pickups', []):
                if p['kind'] not in [w['kind'] for w in me['weapons'] if w]:
                    candidates.append((p, .85, 65))
        for p in o.get('drops', []):
            if p['lands_in'] < 8 and (s.phase != 'late' or s.health < .5):
                candidates.append((p, .6 if s.health < .7 else 1.2, 100))
        options = []
        for p, cost, reach in candidates:
            distance = math.dist(p['pos'][:2], pos[:2])
            safe = math.dist(p['pos'][:2], center) < z['next_radius']-10
            contested = any(math.dist(e['pos'][:2], p['pos'][:2]) < 65 for e in s.enemies)
            if distance < reach and safe and not contested and abs(p['pos'][2]-pos[2]) < 4:
                options.append((distance*cost, p['pos'][:2]))
        if options:
            return min(options, key=lambda p:p[0])[1]
        if mode == 'aggressive' and s.enemies:
            enemy = s.enemies[0]['pos']
            distance = math.dist(enemy[:2], pos[:2])
            if distance > 55:
                return [enemy[k]+(pos[k]-enemy[k])*55/distance for k in range(2)]
        return goal
