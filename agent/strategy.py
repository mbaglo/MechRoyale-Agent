"""[CODEX_ENHANCEMENT_2026-11-21] Placement-first mode transitions and goals."""
import math


class Strategy:
    def __init__(self):
        self.mode = 'balanced'
        # [ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
        # Retain one observed arming destination while approaching the next circle.
        self.arming_target = None

    def arming_route(self, s):
        me, obs = s.me, s.obs
        pos, zone = me['pos'], obs['zone']
        speed = max(1., me['stats']['walk_speed'])
        remaining = math.dist(pos[:2], zone['next_center']) - zone['next_radius'] + 10
        held = {w['kind'] for w in me['weapons'] if w}
        if (remaining <= 10 or s.urgent or obs['t'] >= zone['shrink_start'] or
                held != {'gun'} or None not in me['weapons']):
            self.arming_target = None
            return None
        items = {p['id']: (p, obs['t']) for p in obs.get('pickups', [])}
        if self.arming_target:
            item, seen = self.arming_target
            if obs['t'] - seen < 130/speed and math.dist(pos[:2], item['pos'][:2]) > 5:
                items.setdefault(item['id'], (item, seen))
        best_cost = float('inf')
        self.arming_target = None
        for item, seen in items.values():
            xyz = item['pos']
            if item['kind'] in held or abs(xyz[2] - pos[2]) >= 4:
                continue
            travel = math.dist(pos[:2], xyz[:2])
            inward = math.dist(xyz[:2], zone['next_center']) - zone['next_radius'] + 10
            if not (0 < inward < remaining and travel < 130):
                continue
            # Budget walking both legs with 50% extra path length and 8s in reserve.
            # Keep the ordinary urgency and contestation gates on every observation.
            route = travel + inward
            if (obs['t'] + 1.5*route/speed + 8 >= zone['shrink_start'] or
                    math.dist(xyz[:2], zone['center']) + 10 >= zone['radius'] or
                    any(math.dist(e['pos'][:2], xyz[:2]) < 65 for e in s.enemies)):
                continue
            if route < best_cost:
                self.arming_target, best_cost = (item, seen), route
        return self.arming_target[0]['pos'][:2] if self.arming_target else None

    def choose(self, s):
        close = [e for e in s.enemies if math.dist(e['pos'], s.me['pos']) < 100]
        weak = close and close[0].get('hp', 1400) < s.me['hp']*.5
        if s.health < .42 or len(close) >= 2 or s.urgent:
            self.mode = 'conservative'
        elif s.health > .72 and weak and len(close) == 1:
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
        if s.urgent:
            return goal
        candidates = []
        for p in o.get('cubes', []):
            # [CODEX_ENHANCEMENT_2026-11-21] EXP-010: recover safe visible
            # drops beyond the old 55 m limit, including ordinary gun kills.
            candidates.append((p, 1.0, 130))
        if any(w is None for w in me['weapons']):
            for p in o.get('pickups', []):
                if p['kind'] not in [w['kind'] for w in me['weapons'] if w]:
                    # [CODEX_ENHANCEMENT_2026-11-21] EXP-004: the only
                    # tactical change from V1 is weapon search reach (65 -> 130 m).
                    # Existing zone, enemy-contestation and vertical filters apply.
                    candidates.append((p, .85, 130))
        for p in o.get('drops', []):
            if p['lands_in'] < 8:
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
        arming = self.arming_route(s)
        if arming is not None:
            return arming
        if mode == 'aggressive' and s.enemies:
            enemy = s.enemies[0]['pos']
            distance = math.dist(enemy[:2], pos[:2])
            if distance > 55:
                return [enemy[k]+(pos[k]-enemy[k])*55/distance for k in range(2)]
        return goal
