"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Plan a first equipment pickup during the safe opening of a match.
"""
import math


class EquipmentPlan:
    def __init__(self, world, config):
        self.world = world
        self.config = config
        self.target = None
        self.last_seen = 0.

    def choose(self, s, fallback, last_damage):
        me, obs = s.me, s.obs
        pos, zone = me['pos'], obs['zone']
        now = obs['t']
        gun = next((w for w in me['weapons'] if w and w['kind'] == 'gun'), None)
        if (s.urgent or s.health < .65 or now - last_damage < 3 or gun is None or
                None not in me['weapons'] or now >= zone['shrink_start'] or
                not me['grounded'] or abs(pos[2]-self.world.ground(*pos[:2])) > me['stats']['step_up'] or
                any(math.dist(e['pos'], pos) < 90 for e in s.enemies)):
            self.target = None
            return fallback, None
        # Honor an existing pickup, cube or supply-drop route first.
        if any(item['pos'][:2] == fallback for k in ('pickups','cubes','drops') for item in obs.get(k, [])):
            self.target = None
            return fallback, None
        options = {p['id']: p for p in obs.get('pickups', []) if p['kind'] != 'gun'}
        options.update((c['id'], dict(c, kind='crate')) for c in obs.get('crates', []))
        visible_ids = set(options)
        speed = me['stats']['walk_speed']
        old = self.target
        if (old and now - self.last_seen < 170/speed and
                math.dist(pos[:2], old['pos'][:2]) > 6):
            options.setdefault(old['id'], old)
        best, best_cost = None, float('inf')
        for item in options.values():
            q = item['pos']
            travel = math.dist(pos[:2], q[:2])
            if (travel > 170 or math.dist(q[:2],zone['center']) + 10 >= zone['radius'] or
                    abs(q[2]-self.world.ground(*q[:2])) > me['stats']['step_up'] or
                    any(math.dist(e['pos'][:2], q[:2]) < 65 for e in s.enemies)):
                continue
            inward = max(0, math.dist(q[:2],zone['next_center']) - zone['next_radius'] + 12)
            acquire = 0.
            if item['kind'] == 'crate':
                stats = gun['stats']
                hits = math.ceil(item['hp'] / stats['damage'])
                acquire = hits*stats['cooldown'] + (stats['reload'] if hits > gun['ammo'] else 0)
            duration = 1.5*(travel + inward)/speed + acquire
            if now + duration + 8 >= zone['shrink_start']:
                continue
            # A crate can drop a secondary. Discount its uncertain reward and
            # prefer finishing the current trip when completion times are close.
            cost = duration
            if item['kind'] == 'crate':
                chance = self.config['loot']['crate_weapon_chance']
                if chance <= 0:
                    continue
                cost /= chance
            if old and old['id'] == item['id']:
                cost -= 1
            if cost < best_cost:
                best, best_cost = item, cost
        self.target = best
        if best is None:
            return fallback, None
        if best['id'] in visible_ids:
            self.last_seen = now
        crate_id = best['id'] if best['kind'] == 'crate' else None
        return best['pos'][:2], crate_id
