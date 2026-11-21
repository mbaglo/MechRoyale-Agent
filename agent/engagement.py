"""[ASTRA_ENHANCEMENT_2026-11-21] Coordinate targeting and positioning from one observation."""
import math
from dataclasses import dataclass


@dataclass
class Engagement:
    focus: dict | None
    exposed: int
    can_finish: bool
    spacing: float


def assess(s, config, world, previous_id):
    me = s.me
    gun = next((w for w in me['weapons'] if w and w['kind'] == 'gun'), None)
    if gun is None:
        return None
    stats = gun['stats']
    cube_rules = config['cubes']
    damage = stats['damage'] * (1 + cube_rules['damage_per_cube'] *
                                min(me.get('cubes', 0), cube_rules['stat_cap']))
    origin = [*me['pos'][:2], me['pos'][2] + me['stats']['muzzle_height']]
    focus = None
    best_cost = float('inf')
    best_time = float('inf')
    exposed = 0
    # Bound geometry queries. Enemies retained by the server can be behind walls.
    for enemy in s.enemies[:8]:
        height = config['mech']['height'] * (1 + cube_rules['size_per_cube'] * enemy.get('cubes', 0))
        point = [*enemy['pos'][:2], enemy['pos'][2] + height / 2]
        distance = math.dist(origin, point)
        if not world.clear(origin, point):
            continue
        if distance <= config['weapons']['gun']['range'] or 'laser' in enemy.get('weapons', []):
            exposed += 1
        if distance > stats['range']:
            continue
        shots = max(1, math.ceil(enemy.get('hp', config['mech']['hp']) / damage))
        ammo = gun.get('ammo', 0)
        reload_left = gun.get('reload', 0)
        if reload_left:
            ammo = stats['mag']
        reloads = math.ceil(max(0, shots - ammo) / stats['mag'])
        yaw = math.atan2(point[1] - origin[1], point[0] - origin[0])
        turn = abs(math.remainder(yaw - me['aim'][0], math.tau)) / me['stats']['turn_rate']
        finish_time = (max(turn, reload_left, gun.get('cooldown', 0)) +
                       distance / stats['speed'] + (shots - 1) * stats['cooldown'] +
                       reloads * stats['reload'])
        cost = finish_time - (.45 if enemy['id'] == previous_id else 0)
        if cost < best_cost:
            best_cost, focus, best_time = cost, enemy, finish_time
    # Commit only for a brief finishing opportunity. Crossfire reduces that window.
    can_finish = bool(focus and s.health > .55 and exposed <= 2 and
                      best_time <= (2.5 if exposed < 2 else 1.2))
    spacing = 65.
    arc = next((w for w in me['weapons'] if w and w['kind'] == 'lightning'), None)
    if arc and me['energy'] > arc['stats']['energy'] + 15:
        spacing = arc['stats']['range'] * .8
    return Engagement(focus, exposed, can_finish, spacing)
