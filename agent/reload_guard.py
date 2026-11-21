"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Use idle torso time during a starter-gun reload to keep more shooters in the front armor arc.
"""
import math


def offset(yaw, reference):
    return (yaw-reference+math.pi)%(2*math.pi)-math.pi


def guard_yaw(s, fire_yaw, config, world):
    me = s.me
    arms = [arm for arm in me['weapons'] if arm]
    if len(s.enemies)<2 or len(arms)!=1 or arms[0]['kind']!='gun' or arms[0].get('reload',0)<.4:
        return fire_yaw
    stats,pos = me['stats'],me['pos']
    half = math.radians(stats['front_arc_deg']/2-4)
    if half <= 0:
        return fire_yaw
    eye = [*pos[:2],pos[2]+stats['height']*.5]
    threats = []
    for enemy in s.enemies[:6]:
        ep = enemy['pos']
        bearing = math.atan2(ep[1]-pos[1],ep[0]-pos[0])
        if abs(offset(enemy['aim'][0],bearing+math.pi)) > math.radians(config['vision']['fov_deg']/2):
            continue
        distance = math.dist(pos,ep)
        if not any(config['weapons'][kind].get('range',0) > distance for kind in enemy.get('weapons',())):
            continue
        scale = 1+config['cubes']['size_per_cube']*enemy.get('cubes',0)
        origin = [*ep[:2],ep[2]+config['mech']['muzzle_height']*scale]
        if world.clear(origin,eye):
            threats.append(bearing)
    protected = sum(abs(offset(b,fire_yaw)) <= half for b in threats)
    if protected >= len(threats) or len(threats)<2:
        return fire_yaw
    # Coverage changes at an arc boundary. Keep the firing target protected
    # and leave time for the actual torso to return before the gun is ready.
    chosen = fire_yaw
    remaining = arms[0]['reload']
    for bearing in threats:
        for side in (-1,1):
            heading = offset(bearing+side*half,0)
            back = abs(offset(heading,fire_yaw))
            if back > half or (abs(offset(heading,me['aim'][0]))+back)/stats['turn_rate']+.2 > remaining:
                continue
            count = sum(abs(offset(b,heading)) <= half+1e-8 for b in threats)
            if count > protected or (count == protected and back < abs(offset(chosen,fire_yaw))):
                protected,chosen = count,heading
    return chosen
