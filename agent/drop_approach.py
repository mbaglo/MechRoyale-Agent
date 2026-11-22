"""[CHATGPT_ENHANCEMENT_2026-11-21] Safe advance staging for called supply drops.

The official game announces a drop 25 seconds before it lands, whereas
Strategy.goal previously considered it only in its final eight seconds and
inside 100 metres. A captured drop grants three cubes, full health and energy.
This optional route does not displace the original goal when the bot already
has an eligible pickup, cube, combat pursuit or urgent zone route.
"""
import math


def stage_supply_goal(s, existing_goal, mode, world):
    """[CHATGPT_ENHANCEMENT_2026-11-21] Extend safe drop approach timing.

    Uses only the public drop position and landing countdown. Require a safe
    future circle, clear immediate ground movement, enough time to arrive, no
    tracked opponent and no recent nearby weapon sound or projectile.
    Never infer hidden enemies, distance-to-cover or a guaranteed capture.
    """
    me, obs = s.me, s.obs
    if (s.urgent or mode != 'balanced' or s.health < .80 or s.damage or
            s.enemies or not me['grounded'] or not me['in_zone']):
        return existing_goal
    pos, zone = me['pos'], obs['zone']
    center, radius = zone['next_center'], zone['next_radius']
    # Avoid diverting from *any* already-selected resource or active goal.
    dist_center = math.dist(pos[:2], center)
    safe_radius = max(0., radius - 20.)
    fraction = min(1., safe_radius * .55 / max(1., dist_center))
    quiet_goal = [center[k] + (pos[k] - center[k]) * fraction for k in (0, 1)]
    if math.dist(existing_goal, quiet_goal) > 1e-4:
        return existing_goal

    dangerous_sounds = {'gun', 'npc_gun', 'mortar', 'explosion',
                        'laser', 'laser_charge', 'lightning'}
    if any(sound.get('kind') in dangerous_sounds and
           sound.get('dist') in ('near', 'mid') for sound in obs.get('sounds', [])):
        return existing_goal
    if any(e.get('type') == 'damaged' for e in obs.get('events', [])):
        return existing_goal
    if any(math.dist(b['pos'], pos) < 75. for b in obs.get('projectiles', [])):
        return existing_goal

    walk_speed = me['stats']['walk_speed']
    if walk_speed <= 1.:
        return existing_goal
    choices = []
    for drop in obs.get('drops', []):
        remaining = drop.get('lands_in', 0.)
        # The original 8-second/100-metre route remains the default where
        # available. This window is for prepositioning, not blind late rushes.
        if not 0. < remaining <= 22.:
            continue
        target = drop['pos']
        distance = math.dist(pos[:2], target[:2])
        if (distance > 190. or distance / walk_speed > remaining + 2.5 or
                math.dist(target[:2], center) > radius - 15. or
                abs(target[2] - pos[2]) > 20.):
            continue
        if distance > 1e-5:
            fraction = min(16. / distance, 1.)
            ahead = [pos[k] + fraction * (target[k] - pos[k]) for k in (0, 1)]
            if not world.walkable(pos, ahead, me['stats']):
                continue
        # Prioritize the drop that can be reached before landing, avoiding
        # gratuitous long trips for an identical three-cube reward.
        choices.append((distance / walk_speed, remaining, target[:2]))
    if choices:
        return min(choices, key=lambda item: (item[0], item[1]))[2]
    return existing_goal
