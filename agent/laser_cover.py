"""[ASTRA_ENHANCEMENT_2026-11-21] Find nearby shelter during an observed laser charge."""
import math


class LaserCover:
    def __init__(self, world, config):
        self.world = world
        self.config = config
        self.shooter = None
        self.until = 0.
        self.destination = None

    def goal(self, s):
        me = s.me
        if s.urgent or not me['grounded']:
            return None
        p = me['pos']
        for enemy in s.enemies:
            if not enemy.get('charging'):
                continue
            ex, ey, ez = enemy['pos']
            dx, dy = p[0] - ex, p[1] - ey
            yaw = enemy['aim'][0]
            if (math.hypot(dx, dy) <= self.config['weapons']['laser']['range'] and
                    dx*math.cos(yaw) + dy*math.sin(yaw) > 0 and
                    abs(dx*math.sin(yaw) - dy*math.cos(yaw)) <= 18):
                break
        else:
            self.shooter = None
            return None
        if s.obs['t'] < self.until and self.shooter == enemy['id']:
            return self.destination
        self.shooter, self.until = enemy['id'], s.obs['t'] + .3
        self.destination = None
        stats = me['stats']
        if abs(p[2] - self.world.ground(*p[:2])) > stats['step_up']:
            return None
        size = 1 + self.config['cubes']['size_per_cube'] * enemy.get('cubes', 0)
        source = [ex, ey, ez + self.config['mech']['muzzle_height'] * size]
        if not self.world.clear(source, [p[0], p[1], p[2]+stats['height']*.5]):
            return None
        zone = s.obs['zone']
        heading = math.atan2(dy, dx)
        for distance in (6., 12., 18.):
            for octant in (2,-2,1,-1,3,-3,0,4):
                angle = heading + octant*math.pi/4
                x, y = p[0]+distance*math.cos(angle), p[1]+distance*math.sin(angle)
                if math.dist((x,y),zone['center']) + stats['radius'] > zone['radius']:
                    continue
                z = self.world.ground(x,y)
                if self.world.clear(source, [x,y,z+stats['height']*.5]):
                    continue
                if (not self.world.clear(source, [x,y,z+stats['height']*.95]) and
                        self.world.walkable(p, [x,y,z], stats)):
                    self.destination = [x,y]
                    return self.destination
        return None
