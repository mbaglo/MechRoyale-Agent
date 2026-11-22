"""[CHATGPT_ENHANCEMENT_2026-11-21] Safe approach to recover NPC power cubes.

The scorer awards an NPC two power cubes on death, but the selected bot
shoots distant drones while its navigation goal remains a quiet zone point.
That can strand the reward far from the shooter. This optional approach
moves to a *standoff*, never directly into a live drone, only when all of
the original NeutralFarm threat checks already allow a gun engagement.

All geometry/LOS and target choices are from the current observation and
official arena; this is not a simulated match or a claim of higher score.
"""
import math


def safe_neutral_collection_goal(s, eligible_targets, world, config):
    """[CHATGPT_ENHANCEMENT_2026-11-21] Approach isolated drone loot conservatively.

    Returns a two-element waypoint or None; None preserves the prior goal.
    Changes no gun aim, ammo, upgrade, fire, weapon pickup or supply logic.
    """
    obs, me = s.obs, s.me
    if (s.enemies or s.urgent or s.damage or s.health < .93 or
            not me['grounded'] or not me['in_zone'] or
            not eligible_targets):
        return None

    # The stat bonus stops at the cap; larger hitboxes continue growing.
    if me.get('cubes', 0) >= config['cubes']['stat_cap']:
        return None
    gun = next((w for w in me['weapons'] if w and w['kind'] == 'gun'), None)
    if not gun or gun.get('reload', 0) > .05:
        return None

    pos = me['pos']
    zone = obs['zone']
    center = zone['next_center']
    edge = zone['next_radius'] - 35
    if edge <= 0 or math.dist(pos[:2],center) > edge:
        return None

    # [CHATGPT_FIX_2026-11-21] Keep existing high-value, immediately
    # collectable resources and landing supply drops ahead of a drone chase.
    for cube in obs.get('cubes', []):
        if (math.dist(cube['pos'][:2],pos[:2]) < 130 and
                math.dist(cube['pos'][:2],center) < zone['next_radius']-10 and
                abs(cube['pos'][2]-pos[2]) < 4):
            return None
    if any(w is None for w in me['weapons']):
        held = {w['kind'] for w in me['weapons'] if w}
        for pickup in obs.get('pickups', []):
            if (pickup['kind'] not in held and
                    math.dist(pickup['pos'][:2],pos[:2]) < 130 and
                    math.dist(pickup['pos'][:2],center) < zone['next_radius']-10 and
                    abs(pickup['pos'][2]-pos[2]) < 4):
                return None
    for drop in obs.get('drops', []):
        if (drop['lands_in'] < 8 and
                math.dist(drop['pos'][:2],pos[:2]) < 100 and
                math.dist(drop['pos'][:2],center) < zone['next_radius']-10):
            return None

    # Leave the drone outside its 45 m proactive engagement bubble where
    # possible. Once killed, its *observed* cubes are handled by the
    # existing higher-priority resource-navigation code.
    best = None
    for npc in eligible_targets:
        delta = [npc['pos'][0]-pos[0],npc['pos'][1]-pos[1]]
        distance = math.hypot(*delta)
        if not 65 < distance < 120:
            continue
        if (math.dist(npc['pos'][:2],center) > edge or
                abs(npc['pos'][2]-pos[2]) >= 4):
            continue
        # Gun rounds remaining should finish a drone, avoiding an extended
        # exposure or accidental chase while a multi-second reload begins.
        damage = gun['stats']['damage'] * (
            1 + config['cubes']['damage_per_cube'] *
            min(me.get('cubes',0),config['cubes']['stat_cap'])
        )
        rounds = math.ceil(npc['hp']/max(1.,damage))
        if gun.get('ammo',0) < rounds:
            continue
        standoff = 55.
        point = [npc['pos'][i] - delta[i] * standoff/distance for i in (0,1)]
        if math.dist(point,center) > edge:
            continue
        direction = [delta[0]/distance,delta[1]/distance]
        first_step = [pos[0]+8*direction[0],pos[1]+8*direction[1],pos[2]]
        if not world.walkable(pos, first_step, me['stats']):
            continue
        if best is None or distance < best[0]:
            best = (distance, point)

    return None if best is None else best[1]
