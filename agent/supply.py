"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Finish a banked supply capture when no observed opponent can reach its ring in time.
"""
import math


def finishing_drop(s, config):
    me = s.me
    if s.urgent or not me['grounded']:
        return None
    for drop in s.obs.get('drops',[]):
        if drop.get('holder') != me['id'] or drop['lands_in']>0 or drop.get('progress',0)<=0:
            continue
        center,radius = drop['pos'][:2],drop['radius']
        left = drop['capture_s']-drop['progress']
        if not 0 < left <= min(1.5,drop['capture_s']/2) or math.dist(me['pos'][:2],center)>radius:
            continue
        # Use visible speed and the base sprint speed with a reaction margin.
        # The protocol does not reveal rival movement upgrades.
        for enemy in s.enemies:
            speed = max(config['mech']['boost_speed'],math.hypot(*enemy['vel'][:2]))
            if enemy.get('charging') or math.dist(enemy['pos'][:2],center) <= radius+speed*(left+.35):
                break
        else:
            return drop
    return None


def stay_inside(s, drop, move, boost, world):
    me = s.me
    stats,pos = me['stats'],me['pos']
    vel = me['vel'][:2]
    x,y = pos[:2]
    center = drop['pos'][:2]
    speed = stats['boost_speed' if boost else 'walk_speed']
    left = drop['capture_s']-drop['progress']
    for _ in range(min(8,math.ceil(left/.05))):
        delta = [speed*move[k]-vel[k] for k in (0,1)]
        fraction = min(1.,stats['ground_accel']*.05/max(1e-8,math.hypot(*delta)))
        vel = [vel[k]+fraction*delta[k] for k in (0,1)]
        x,y = x+.05*vel[0],y+.05*vel[1]
        if math.dist([x,y],center) >= drop['radius']-.25:
            distance = math.dist(pos[:2],center)
            if distance>.1 and world.walkable(pos,center,stats):
                return [(center[k]-pos[k])/distance for k in (0,1)],False
            return [0.,0.],False
    return move,boost
