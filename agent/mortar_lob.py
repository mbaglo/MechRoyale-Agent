"""[CHATGPT_ENHANCEMENT_2026-11-21] Checked mortar lob trajectories.

The official world permits arcing mortar rounds over buildings. A straight-line
vision test cannot establish whether such a shot is possible. Uses only observed
target positions/velocities, live weapon/mech stats and official map geometry.

This is deliberately opt-in for occluded targets; the prior direct-fire behavior
is preserved outside that case.
"""
import math


def mortar_lob_solution(me, target, world, stats):
    """[CHATGPT_FIX_2026-11-21] Return (yaw,pitch) for a safe covered-target lob.

    This is a sampled projectile/terrain approximation, not authoritative physics.
    Only accept solutions whose predicted impact is close to the observed target.
    """
    speed = float(stats.get('speed', 0.))
    gravity = float(stats.get('gravity', 0.))
    if speed <= 0 or gravity <= 0:
        return None
    pos = me['pos']
    height = me.get('stats', {}).get('height', 9.)
    origin = [pos[0], pos[1], pos[2] + height + .5]
    muzzle_offset = me.get('stats', {}).get('radius', 2.5) + .5
    min_pitch = me.get('stats', {}).get('min_pitch', -1.0)
    max_pitch = me.get('stats', {}).get('max_pitch', 1.5)
    if max_pitch <= min_pitch:
        return None
    opponent_pos = target['pos']
    opponent_velocity = target.get('vel', [0., 0., 0.])
    center_z = 4.5 * (1 + .05*target.get('cubes', 0))
    if target.get('kind') == 'npc':
        center_z = 1.75
    point = [opponent_pos[0], opponent_pos[1], opponent_pos[2]+center_z]
    splash = float(stats.get('splash_radius', 7.))
    if math.dist(point[:2], pos[:2]) <= splash*2 + 12:
        return None

    # [CHATGPT_FIX_2026-11-21] Lead EACH arc independently. Previously
    # the high-angle solution inherited the low-angle flight time, which
    # could make a long, lofted shot miss a moving opponent.
    options = []
    for branch in (0, 1):
        flight_time = math.dist(point[:2],origin[:2])/speed
        solution = None
        for iteration in range(4):
            predicted = [point[k]+opponent_velocity[k]*min(3.,flight_time)
                         for k in range(3)]
            dx, dy = predicted[0]-origin[0], predicted[1]-origin[1]
            horizontal = math.hypot(dx,dy)
            dz = predicted[2]-origin[2]
            if not 15. < horizontal < (speed*speed/gravity)*.99:
                break
            square = speed**4 - gravity*(gravity*horizontal**2 + 2*dz*speed**2)
            if square < 0:
                break
            root = math.sqrt(square)
            guess = math.atan2(
                speed**2-root if branch == 0 else speed**2+root,
                gravity*horizontal
            )
            angle = guess
            # Refine the analytical arc for the 3m displaced muzzle used
            # by the game's projectile launcher.
            for _newton in range(5):
                def error(theta):
                    cc, ss = math.cos(theta), math.sin(theta)
                    if cc <= .08:
                        return float('inf')
                    t = (horizontal-muzzle_offset*cc)/(speed*cc)
                    if t <= 0:
                        return float('inf')
                    landing_z = (origin[2]+muzzle_offset*ss+
                                 speed*ss*t - gravity*t*t/2)
                    return landing_z - predicted[2]
                value = error(angle)
                if not math.isfinite(value):
                    break
                derivative = (error(angle+.0005)-error(angle-.0005))/.001
                if not math.isfinite(derivative) or abs(derivative) < .02:
                    break
                adjusted = angle-value/derivative
                if not math.isfinite(adjusted) or abs(adjusted-angle) > .5:
                    break
                angle = adjusted
            if not (min_pitch <= angle <= max_pitch):
                break
            c = math.cos(angle)
            t = (horizontal-muzzle_offset*c)/(speed*c)
            if t <= 0 or t > 7.:
                break
            yaw = math.atan2(dy,dx)
            solution = (t, yaw, angle, predicted, horizontal)
            if abs(t-flight_time) < .02:
                break
            flight_time = t
        if solution is not None:
            options.append(solution)

    if not options:
        return None
    # [CHATGPT_FIX_2026-11-21] The first clear ballistic arc is preferred.
    # The direct vision ray may hit a wall, but the projectile must not.
    for t, yaw, pitch, predicted, horizontal in options:
        c, sn = math.cos(pitch), math.sin(pitch)
        hx, hy = math.cos(yaw), math.sin(yaw)
        shot = [origin[0]+muzzle_offset*c*hx,
                origin[1]+muzzle_offset*c*hy,
                origin[2]+muzzle_offset*sn]
        if world.solid(*shot) or shot[2] < world.ground(*shot[:2]):
            continue
        clear = True
        # Use 32 checks to keep bounded CPU usage in the 50ms tick budget.
        for k in range(1, 33):
            ft = t*k/32.
            loc = [shot[0]+speed*c*hx*ft,
                   shot[1]+speed*c*hy*ft,
                   shot[2]+speed*sn*ft-gravity*ft*ft/2]
            if world.solid(*loc) or loc[2] < world.ground(*loc[:2]):
                clear = False
                break
        if clear:
            last = loc
            if math.dist(last,predicted) <= max(2.5,splash*.55):
                return yaw,pitch
    return None
