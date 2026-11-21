"""[CODEX_ENHANCEMENT_2026-11-21] Placement-first mode transitions and goals."""
import math


class Strategy:
    def __init__(self):
        self.mode = 'balanced'
        # [ASTRA_ENHANCEMENT_2026-11-21] Static ground loot can leave our vision wedge.
        self.loot_memory = {'pickups': {}, 'cubes': {}}

    def ground_loot(self, s, field):
        """Keep a short-lived destination after losing sight of a static item."""
        now = s.obs['t']
        visible = {item['id']: item for item in s.obs.get(field, [])}
        pos = s.me['pos']
        # One walk across the existing search radius is a useful upper bound.
        lifetime = min(15., 130 / max(1., s.me['stats']['walk_speed']))
        memory = self.loot_memory[field]
        for item_id, (seen, item) in list(memory.items()):
            if item_id in visible:
                continue
            at_destination = (math.dist(pos[:2], item['pos'][:2]) < 8 and
                              abs(pos[2] - item['pos'][2]) <= 4)
            if now - seen > lifetime or at_destination:
                del memory[item_id]
        for item_id, item in visible.items():
            memory[item_id] = (now, item)
        if len(memory) > 64:
            # Keep recent sightings for future frames. All current sightings
            # remain eligible for this decision even in a dense late-game pile.
            for item_id in sorted(memory, key=lambda key: memory[key][0])[:-64]:
                del memory[item_id]
        return [*visible.values(), *(item for key, (_, item) in memory.items() if key not in visible)]

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
        cubes = self.ground_loot(s, 'cubes')
        pickups = self.ground_loot(s, 'pickups')
        if s.urgent:
            return goal
        candidates = []
        for p in cubes:
            # [CODEX_ENHANCEMENT_2026-11-21] EXP-010: recover safe visible
            # drops beyond the old 55 m limit, including ordinary gun kills.
            candidates.append((p, 1.0, 130))
        if any(w is None for w in me['weapons']):
            for p in pickups:
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
        if mode == 'aggressive' and s.enemies:
            enemy = s.enemies[0]['pos']
            distance = math.dist(enemy[:2], pos[:2])
            if distance > 55:
                return [enemy[k]+(pos[k]-enemy[k])*55/distance for k in range(2)]
        return goal
