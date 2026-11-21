"""[CODEX_ENHANCEMENT_2026-11-21] Placement-first mode transitions and goals."""
import math


class Strategy:
    def __init__(self):
        self.mode = 'balanced'

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
        # [CHATGPT_FIX_2026-11-21] V1-specific, narrow crossfire escape.
        # Two opponents opposite one another can cancel the original local
        # planner's separation rewards while the zone goal equals our position.
        # Keep the V1 movement, collision, boosting, combat and mode logic.
        if mode == 'conservative' and not s.urgent:
            threats = [
                e for e in s.enemies
                if math.dist(e['pos'][:2], pos[:2]) < 135
            ]
            if len(threats) >= 2:
                safe_radius = max(0., z['next_radius'] - 8.)
                nearest_now = min(
                    math.dist(e['pos'][:2], pos[:2]) for e in threats
                )
                best = None
                for i in range(16):
                    angle = i * math.tau / 16
                    # [CHATGPT_ENHANCEMENT_2026-11-21] Select a nearby
                    # separation goal; the original Navigator still checks
                    # map geometry and projectile danger before moving.
                    candidate = [
                        pos[0] + 24. * math.cos(angle),
                        pos[1] + 24. * math.sin(angle),
                    ]
                    zone_dist = math.dist(candidate, center)
                    if (zone_dist > safe_radius
                            and zone_dist > math.dist(pos[:2], center)):
                        continue
                    distances = []
                    for e in threats:
                        velocity = e.get('vel', [0, 0, 0])
                        projected = [
                            e['pos'][0] + .75 * velocity[0],
                            e['pos'][1] + .75 * velocity[1],
                        ]
                        distances.append(math.dist(candidate, projected))
                    nearest = min(distances)
                    # The minimum discourages escaping toward a flanker;
                    # average spacing differentiates equally safe routes.
                    score = nearest * 3. + sum(
                        min(160., distance) for distance in distances
                    ) / len(distances)
                    # Allow original zone logic to dominate near its edge.
                    score -= max(0., zone_dist - safe_radius * .8) * 2.
                    if best is None or score > best[0]:
                        best = (score, candidate)
                if best is not None:
                    # Do not take a sideways detour that is significantly
                    # closer to the nearest threat than staying put.
                    if min(
                        math.dist(best[1], e['pos'][:2])
                        for e in threats
                    ) >= max(0., nearest_now - 8.):
                        return best[1]

        if s.urgent:
            return goal
        candidates = []
        for p in o.get('cubes', []):
            candidates.append((p, 1.0, 55))
        if any(w is None for w in me['weapons']):
            for p in o.get('pickups', []):
                if p['kind'] not in [w['kind'] for w in me['weapons'] if w]:
                    candidates.append((p, .85, 65))
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
