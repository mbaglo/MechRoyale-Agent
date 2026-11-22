"""[CHATGPT_ENHANCEMENT_2026-11-21] Opportunistic safe secondary-weapon upgrades.

The official protocol permits an atomic take+drop swap when both weapon slots
are full. Prefer a longer-range laser over a short-range lightning gun while
healthy and not engaged; never surrender the required starter gun.
"""
import math


def safe_laser_replacements(s):
    """[CHATGPT_ENHANCEMENT_2026-11-21] List observed safe laser upgrade options.

    The stationary, vulnerable swap only happens outside combat, while the mech
    is safely grounded in-zone. No unobserved or inferred item is ever targeted.
    """
    me, obs = s.me, s.obs
    weapons = me['weapons']
    if (len(weapons) < 2 or not all(weapons) or
            weapons[0]['kind'] != 'gun' or weapons[1]['kind'] != 'lightning' or
            s.urgent or s.enemies or s.health < .85 or
            not me['in_zone'] or not me['grounded']):
        return []

    if any(e.get('type') == 'damaged' for e in obs.get('events', [])):
        return []

    hostile = ('gun', 'mortar', 'laser', 'laser_charge', 'lightning',
               'explosion', 'npc_gun', 'boost', 'jet')
    if any(sound.get('kind') in hostile and sound.get('dist') in ('near', 'mid')
           for sound in obs.get('sounds', [])):
        return []

    if any(math.dist(p['pos'], me['pos']) < 80
           for p in obs.get('projectiles', [])):
        return []

    if any(drop.get('holder') == me['id'] and drop.get('progress', 0) > 0
           for drop in obs.get('drops', [])):
        return []

    return [p for p in obs.get('pickups', []) if p['kind'] == 'laser']
