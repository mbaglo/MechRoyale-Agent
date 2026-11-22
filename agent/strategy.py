"""[CODEX_ENHANCEMENT_2026-11-21] Placement-first mode transitions and goals."""
import math


class Strategy:
    def __init__(self, world=None):
        self.mode = 'balanced'
        self.world = world

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
            if distance < reach and safe and not contested:
                same_height = abs(p['pos'][2]-pos[2]) < 4
                if same_height or (self.world and me['grounded'] and 'lands_in' not in p):
                    options.append((distance*cost,p['pos'],same_height))
        # [ASTRA_FIX_2026-11-21] [CODEX_FIX_2026-11-21] The 4 m collection
        # tolerance applies on arrival. Other ground loot can be uphill or downhill.
        geometry_checks=0
        for _,location,same_height in sorted(options,key=lambda v:v[0]):
            if same_height:
                return location[:2]
            if geometry_checks>=2:
                continue
            step=me['stats']['step_up']
            if abs(pos[2]-self.world.ground(*pos[:2]))>step or abs(location[2]-self.world.ground(*location[:2]))>step:
                continue
            geometry_checks+=1
            if self.world.walkable(pos,location,me['stats']):
                return location[:2]
        if mode == 'aggressive' and s.enemies:
            enemy = s.enemies[0]['pos']
            distance = math.dist(enemy[:2], pos[:2])
            if distance > 55:
                return [enemy[k]+(pos[k]-enemy[k])*55/distance for k in range(2)]
        return goal
