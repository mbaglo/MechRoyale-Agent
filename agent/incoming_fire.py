"""[CHATGPT_ENHANCEMENT_2026-11-22] Anticipate observed projectile impacts.

In the official rules enemy mortar shells fall under gravity and damage within
their splash radius, while gun bullets travel straight. The original navigator
treated every projectile as linear and forced a stationary command at quiet
goals even when an incoming bullet was on course to hit.

This module uses ONLY visible projectiles and the published world collision
queries. It is a bounded short-horizon approximation, not match simulation.
"""
import math


def mortar_impacts(projectiles, world, config, me):
    """[CHATGPT_ENHANCEMENT_2026-11-22] Predict imminent visible shell impacts.

    Return impact time, x/y/z and splash radius. Predict no farther than 1.2s,
    examine at most four nearby shells, and never invent unseen threats.
    """
    st = config.get('weapons', {}).get('mortar', {})
    gravity = float(st.get('gravity', 22.))
    splash = float(st.get('splash_radius', 7.))
    if gravity <= 0 or splash <= 0:
        return []
    pos = me['pos']
    shells = [
        p for p in projectiles
        if p.get('kind') == 'mortar' and math.dist(p['pos'][:2],pos[:2]) < 125
    ]
    shells.sort(key=lambda p:math.dist(p['pos'][:2],pos[:2]))
    results = []
    for p in shells[:4]:
        origin, velocity = p['pos'], p['vel']
        # At each substep include gravity and stop at the FIRST collision.
        for step in range(1,25):
            t = step*.05
            x = origin[0] + velocity[0]*t
            y = origin[1] + velocity[1]*t
            z = origin[2] + velocity[2]*t - gravity*t*t*.5
            ground = world.ground(x,y)
            if z <= ground or world.solid(x,y,z):
                # A wall hit is a real impact, not a shell that flies through it.
                results.append((t,x,y,max(z,ground)+.4,splash))
                break
    return results


def incoming_bullet(projectiles, me):
    """[CHATGPT_FIX_2026-11-22] Detect an imminent straight-shot threat.

    This specifically avoids the navigator's unconditional idle override when
    a bullet is about to cross the mech's cylinder in the next 0.65 seconds.
    """
    pos = me['pos']
    stats = me['stats']
    for p in projectiles[:20]:
        if p.get('kind') == 'mortar':
            continue
        loc, vel = p['pos'],p['vel']
        denom = vel[0]**2+vel[1]**2
        if denom < 1:
            continue
        t = ((pos[0]-loc[0])*vel[0]+(pos[1]-loc[1])*vel[1])/denom
        if not 0 <= t <= .65:
            continue
        x,y,z = (loc[k]+vel[k]*t for k in range(3))
        if (math.hypot(pos[0]-x,pos[1]-y) < stats.get('radius',2.5)+2 and
                pos[2]-1 <= z <= pos[2]+stats.get('height',9)+1):
            return True
    return False


def explosive_risk(pos, velocity, direction, stats, impacts, world):
    """[CHATGPT_ENHANCEMENT_2026-11-22] Estimate blast exposure after movement.

    The candidate's horizontal acceleration is limited by the published stat.
    Only imminent impacts are considered. Walls are tested to respect the
    published rule that they block blast damage.
    """
    if not impacts:
        return 0.
    total = 0.
    walk_speed = float(stats.get('walk_speed',11.7))
    acceleration = float(stats.get('ground_accel',22.))
    for t,ix,iy,iz,splash in impacts:
        x,y = pos[:2]
        vx,vy = velocity[:2]
        desired = (direction[0]*walk_speed,direction[1]*walk_speed)
        dt = t/max(1,math.ceil(t/.05))
        for _ in range(max(1,math.ceil(t/.05))):
            dvx,dvy = desired[0]-vx,desired[1]-vy
            length = math.hypot(dvx,dvy)
            if length > 1e-8:
                proportion = min(1.,acceleration*dt/length)
                vx += dvx*proportion
                vy += dvy*proportion
            x += vx*dt
            y += vy*dt
        distance = math.hypot(x-ix,y-iy)
        reach = splash+float(stats.get('radius',2.5))
        if distance >= reach:
            continue
        if not world.clear([ix,iy,iz],[x,y,pos[2]+stats.get('height',9)*.5]):
            continue
        # Strong enough to override passive inner-zone hold when exposed.
        # Early impending impacts deserve more urgency than distant ones.
        total += (reach-distance)*11.*(1. if t < .85 else .7)
    return total


def immediate_blast_warning(me, impacts):
    """[CHATGPT_FIX_2026-11-22] Only interrupt quiet idle near a blast."""
    pos,stats = me['pos'],me['stats']
    speed = float(stats.get('walk_speed',11.7))
    radius = float(stats.get('radius',2.5))
    return any(
        math.hypot(pos[0]-x,pos[1]-y) <
        splash+radius+speed*min(t,.9)
        for t,x,y,z,splash in impacts
    )
