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
        """
        Select a reachable short-term goal without changing the existing
        loot, zone, aggression, or combat policies.

        [CHATGPT_FIX_2026-11-21] Opposite approaching threats can cancel
        the old away-vector, leaving the mech stationary while surrounded.
        Evaluate already-validated escape sectors in that case.
        [CHATGPT_ENHANCEMENT_2026-11-21] Compare predicted enemy positions,
        zone safety, and threat weighting before selecting an escape sector.
        """
        o, me = s.obs, s.me
        pos = me['pos']
        z = o['zone']
        center = z['next_center']
        radius = max(0, z['next_radius'] - 20)
        d = math.dist(pos[:2], center)

        # Preserve the original future-zone destination and inward buffer.
        fraction = min(1, radius * .55 / max(d, 1))
        goal = [center[k] + (pos[k] - center[k]) * fraction for k in range(2)]

        # Preserve vector-based retreat as the default high-pressure behavior.
        if s.pressure > .8 and s.enemies and not s.urgent:
            weights = s.threat_weights or {}
            vx = sum(
                (pos[0] - e['pos'][0])
                / max(1, math.dist(pos[:2], e['pos'][:2]))
                * weights.get(e['id'], .2)
                for e in s.enemies
            )
            vy = sum(
                (pos[1] - e['pos'][1])
                / max(1, math.dist(pos[:2], e['pos'][:2]))
                * weights.get(e['id'], .2)
                for e in s.enemies
            )
            length = math.hypot(vx, vy)
            if length > .1:
                goal = [pos[0] + vx / length * 55,
                        pos[1] + vy / length * 55]
                offset = math.dist(goal, center)
                if offset > radius and offset > 0:
                    goal = [center[k] + (goal[k] - center[k])
                            * radius / offset for k in range(2)]

            # [CHATGPT_FIX_2026-11-21] When threats are on opposite sides,
            # their retreat vectors cancel. Standing still is dangerous.
            # Only select sectors previously marked walkable by Observer.
            # Also consider multiple pursuit/crossfire instead of trusting
            # a summed vector whose magnitude hides surrounding enemies.
            if ((length <= .1 or s.crossfire >= .45 or s.pursuing >= 2)
                    and s.escape_routes):
                best = None
                for direction in s.escape_routes:
                    # A 22-meter goal is deliberately local. The bounded
                    # Router and the original 16-direction planner remain
                    # responsible for obstacle avoidance.
                    candidate = [pos[0] + direction[0] * 22,
                                 pos[1] + direction[1] * 22]
                    future_distance = math.dist(candidate, center)
                    # A retreat must not worsen imminent zone exposure.
                    if future_distance > radius and future_distance > d:
                        continue

                    # Minimize proximity to each observed threat, using
                    # projected positions but no hidden enemy information.
                    score = 0.0
                    for enemy in s.enemies:
                        enemy_pos = enemy['pos']
                        velocity = enemy.get('vel', [0, 0, 0])
                        predicted = [
                            enemy_pos[0] + velocity[0] * .75,
                            enemy_pos[1] + velocity[1] * .75,
                        ]
                        separation = math.dist(candidate, predicted)
                        threat = max(.1, weights.get(enemy['id'], .2))
                        # Saturation prevents one distant enemy from
                        # outweighing an immediate crossfire escape.
                        score += threat * min(separation, 110)
                        if separation < 35:
                            score -= threat * (35 - separation) * 3

                    # Prefer leaving open space in the future circle.
                    score -= max(0, future_distance - radius * .75) * 1.5
                    # Preserve directional continuity when viable.
                    if length > .1:
                        score += 4 * (
                            direction[0] * vx / length
                            + direction[1] * vy / length
                        )
                    if best is None or score > best[0]:
                        best = (score, candidate)

                if best is not None:
                    goal = best[1]

        # Preserve high-priority zone and emergency overrides.
        if s.urgent:
            return goal
        if s.emergency or s.pressure >= self.tuning.conservative_pressure:
            return goal

        # Preserve the original phase-aware loot selection.
        candidates = []
        for p in o.get('cubes', []):
            candidates.append((p, 1.0, 25 if s.phase == 'late' else 55))
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
            safe = math.dist(p['pos'][:2], center) < z['next_radius'] - 10
            contested = any(
                math.dist(e['pos'][:2], p['pos'][:2]) < 65
                for e in s.enemies
            )
            if (distance < reach and safe and not contested
                    and abs(p['pos'][2] - pos[2]) < 4):
                options.append((distance * cost, p['pos'][:2]))
        if options:
            return min(options, key=lambda p: p[0])[1]

        # Preserve isolated-enemy pursuit in aggressive mode.
        if mode == 'aggressive' and s.enemies:
            enemy = s.enemies[0]['pos']
            distance = math.dist(enemy[:2], pos[:2])
            if distance > 55:
                return [
                    enemy[k] + (pos[k] - enemy[k]) * 55 / distance
                    for k in range(2)
                ]
        return goal
