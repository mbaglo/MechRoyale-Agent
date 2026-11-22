"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
[CHATGPT_ENHANCEMENT_2026-11-21] Reuse previously scored 2.81 shelter policy alongside 2.92 winner.\nFind a short ground route that shelters a recovering mech from its known opponent.
"""
import math


class RecoveryCover:
    def __init__(self, world, config):
        self.world = world
        self.config = config
        self.reset()

    def reset(self):
        self.shooter = None
        self.destination = None
        self.recheck = 0.
        self.last_sheltered = -float('inf')

    def shielded(self, source, pos, height):
        return all(not self.world.clear(source, [pos[0],pos[1],pos[2]+height*f])
                   for f in (.5,.95))

    def route(self, s):
        me, o = s.me, s.obs
        pos, stats, zone = me['pos'], me['stats'], o['zone']
        now = o['t']
        if (not s.recovery_window or s.urgent or not me['grounded'] or len(s.enemies) > 1 or
                any(math.dist(p['pos'],pos) < 30 for p in o.get('projectiles', [])) or
                any(d['lands_in'] <= 0 and math.dist(pos[:2],d['pos'][:2]) <= d['radius']
                    for d in o.get('drops', []))):
            self.reset()
            return None, False
        if not s.enemies:
            # A brief hold can complete regeneration after an observed pursuer disappears.
            return None, now-self.last_sheltered < 2.
        enemy = s.enemies[0]
        if math.dist(pos,enemy['pos']) < 65:
            self.reset()
            return None, False
        ex, ey, ez = enemy['pos']
        size = 1 + self.config['cubes']['size_per_cube']*enemy.get('cubes',0)
        source = [ex,ey,ez+self.config['mech']['muzzle_height']*size]
        if self.shielded(source,pos,stats['height']):
            self.last_sheltered = now
            return None, True
        if enemy['id'] == self.shooter and now < self.recheck:
            return self.destination, False
        self.shooter, self.recheck, self.destination = enemy['id'], now+.4, None
        if abs(pos[2]-self.world.ground(*pos[:2])) > stats['step_up']:
            return None, False
        heading = math.atan2(pos[1]-ey,pos[0]-ex)
        for distance in (6,12,18,24,30):
            for sector in (2,-2,1,-1,3,-3,0,4):
                angle = heading + sector*math.pi/4
                x, y = pos[0]+distance*math.cos(angle), pos[1]+distance*math.sin(angle)
                if math.dist([x,y],zone['center']) + 8 >= zone['radius']:
                    continue
                inward = max(0,math.dist([x,y],zone['next_center'])-zone['next_radius']+15)
                if now + (distance+inward)/stats['walk_speed'] + 8 >= zone['shrink_end']:
                    continue
                site = [x,y,self.world.ground(x,y)]
                if self.shielded(source,site,stats['height']) and self.world.walkable(pos,site,stats):
                    self.destination = site[:2]
                    return self.destination, False
        return None, False
