"""[CODEX_ENHANCEMENT_2026-11-21] Intercepts, weapon control and fire discipline."""
import math
from .reload_guard import guard_yaw


def angle_delta(a, b):
    return (a-b+math.pi) % (2*math.pi)-math.pi


def intercept(origin, target, velocity, speed):
    r = [target[k]-origin[k] for k in range(3)]
    a = sum(v*v for v in velocity)-speed*speed
    b = 2*sum(r[k]*velocity[k] for k in range(3))
    c = sum(v*v for v in r)
    roots = []
    if abs(a) < 1e-8:
        if abs(b) > 1e-8:
            roots = [-c/b]
    elif b*b-4*a*c >= 0:
        q = math.sqrt(b*b-4*a*c)
        roots = [(-b-q)/(2*a),(-b+q)/(2*a)]
    t = min((v for v in roots if v >= 0), default=0)
    return [target[k]+velocity[k]*min(t,3) for k in range(3)]


class Combat:
    def __init__(self, config, world):
        self.config, self.world = config, world
        self.target_id = None
        # [CODEX_ENHANCEMENT_2026-11-21] EXP-009: finish looking toward a
        # heard attacker before returning to the original no-target scan.
        self.attention_yaw = 0.
        self.attention_until = -float('inf')
        self.near_warning_yaw = 0.
        self.near_warning_until = -float('inf')

    def act(self, s, mode):
        me, obs = s.me, s.obs
        origin = list(me['pos'])
        origin[2] += me['stats']['muzzle_height']
        targets = list(s.enemies)
        if not targets and mode != 'conservative':
            targets = [dict(c, kind='crate', vel=[0,0,0]) for c in obs.get('crates', [])
                       if math.dist(c['pos'],me['pos']) < 65]
        def priority(e):
            d = math.dist(e['pos'],me['pos'])
            return d + e.get('hp',1400)*.025 - (15 if e['id'] == self.target_id else 0)
        targets.sort(key=priority)
        target = None
        for e in targets[:8]:
            height = {'mech':4.5*(1+.05*e.get('cubes',0)), 'npc':1.75, 'crate':1.2}[e['kind']]
            point = [e['pos'][0],e['pos'][1],e['pos'][2]+height]
            if self.world.clear(origin,point):
                target = e
                break
        reload = any(w and w['kind']=='gun' and w.get('reload',0)==0 and
                     (w.get('ammo',0)==0 or (not s.enemies and w.get('ammo',0)<w['stats']['mag']*.6)) for w in me['weapons'])
        if target is None:
            # Face a heard attacker before scanning; preserve front armor.
            bearings = [e['bearing'] for e in obs.get('events',[]) if e['type']=='damaged' and e.get('bearing') is not None]
            sounds = [e for e in obs.get('sounds',[]) if e['kind'] in ('gun','laser_charge','lightning')]
            # [CODEX_FIX_2026-11-21] One 0.1-second command cannot complete
            # a large defensive turn at the protocol's finite torso turn rate.
            if bearings or sounds:
                self.attention_yaw = bearings[-1] if bearings else sounds[-1]['bearing']
                turn_rate = me['stats'].get('turn_rate',self.config['mech']['turn_rate'])
                self.attention_until = obs['t']+max(.6,min(2.,math.pi/max(.1,turn_rate)+.2))
                near = [sound for sound in sounds if sound.get('dist') in ('near','mid')]
                if bearings or near:
                    self.near_warning_yaw = bearings[-1] if bearings else near[-1]['bearing']
                    self.near_warning_until = self.attention_until
            yaw = self.attention_yaw if obs['t']<self.attention_until else obs['t']*.6
            # [ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
            # The game reports a tracked mech's current position behind cover.
            # Keep the front arc and view on it until it emerges or the track expires.
            if len(s.enemies) == 1:
                enemy = s.enemies[0]
                delta = [enemy['pos'][k]-origin[k] for k in range(3)]
                scale = 1+self.config['cubes']['size_per_cube']*enemy.get('cubes',0)
                delta[2] += self.config['mech']['height']*.5*scale
                bearing = math.atan2(delta[1],delta[0])
                if math.hypot(*delta[:2]) < self.config['weapons']['gun']['range']:
                    if (obs['t'] < self.near_warning_until and
                            abs(angle_delta(bearing,self.near_warning_yaw)) > math.pi/4):
                        return [self.near_warning_yaw,0.],[False,False],reload
                    pitch = math.atan2(delta[2],math.hypot(*delta[:2]))
                    pitch = max(me['stats']['min_pitch'],min(me['stats']['max_pitch'],pitch))
                    return [bearing,pitch],[False,False],reload
            return [angle_delta(yaw,0),0.], [False,False], reload
        self.target_id = target['id']
        height = 1.2 if target['kind']=='crate' else 4.5*(1+.05*target.get('cubes',0))
        point = [target['pos'][0], target['pos'][1], target['pos'][2]+height]
        distance = math.dist(origin,point)
        weapons = me['weapons']
        # A ready/charging secondary takes aim priority; gun otherwise.
        selected = next((w for w in weapons if w and w['kind']!='gun' and
                         (w.get('cooldown',0)<=.1 or w.get('charge',0)>0) and
                         distance < w['stats'].get('range',220)), None)
        selected = selected or next((w for w in weapons if w), None)
        aim_point = point
        pitch = None
        if selected and selected['kind']=='gun':
            aim_point = intercept(origin, point, target.get('vel',[0,0,0]), selected['stats']['speed'])
        elif selected and selected['kind']=='mortar':
            st = selected['stats']
            aim_point = intercept(origin,point,target.get('vel',[0,0,0]),st['speed'])
            r = math.dist(origin[:2],aim_point[:2]); dz = aim_point[2]-origin[2]
            v, g = st['speed'], st['gravity']
            discriminant = v**4-g*(g*r*r+2*dz*v*v)
            if discriminant >= 0 and r > 1:
                pitch = math.atan((v*v-math.sqrt(discriminant))/(g*r))
        yaw = math.atan2(aim_point[1]-origin[1],aim_point[0]-origin[0])
        pitch = pitch if pitch is not None else math.atan2(aim_point[2]-origin[2],math.dist(origin[:2],aim_point[:2]))
        pitch = max(me['stats']['min_pitch'],min(me['stats']['max_pitch'],pitch))
        aligned = abs(angle_delta(yaw,me['aim'][0])) < math.atan2(2,max(distance,1))+.015 and abs(pitch-me['aim'][1]) < .04
        retreat = mode=='conservative' and distance > 55
        fire = [False,False]
        for i,w in enumerate(weapons):
            if not w:
                continue
            kind, st = w['kind'], w['stats']
            allowed = aligned and not retreat and w.get('cooldown',0)<=.1
            if kind=='gun':
                # Do not fire the gun along the mortar's elevated trajectory.
                # [CODEX_ENHANCEMENT_2026-11-21] EXP-012: allow aligned gun
                # counterpressure while retreating; all other weapons keep the
                # original retreat veto. No target/LOS still means no firing.
                gun_allowed = aligned and w.get('cooldown',0)<=.1
                fire[i] = gun_allowed and distance < st['range'] and w.get('ammo',0)>0 and not w.get('reload',0) and (selected is None or selected['kind']!='mortar')
            elif kind=='lightning':
                fire[i] = bool(not retreat and distance < st['range'] and me['energy'] > st['energy']+15 and abs(angle_delta(yaw,me['aim'][0])) < math.radians(st['cone_deg'])*.45 and w.get('cooldown',0)<=.1)
            elif kind=='laser':
                charge = w.get('charge',0)
                fire[i] = bool(not retreat and distance < st['range'] and w.get('cooldown',0)<=.1 and
                               (charge < st['charge'] or not aligned))
            elif kind=='mortar':
                r = math.dist(origin[:2],aim_point[:2]); dz = aim_point[2]-origin[2]
                possible = st['speed']**4-st['gravity']*(st['gravity']*r*r+2*dz*st['speed']**2)>=0
                fire[i] = bool(allowed and selected is w and possible and distance > st['splash_radius']*2+8)
        # [ASTRA_ENHANCEMENT_2026-11-21] Preserve an imminent regeneration window
        # while tracking a distant target. Keep close defense and finishing shots.
        if s.recovery_window and not s.urgent and not any(w and w.get('charge',0) > 0 for w in weapons):
            gun = next((w for w in weapons if w and w['kind'] == 'gun'), None)
            damage = gun['stats']['damage'] if gun else 0
            cubes = self.config['cubes']
            damage *= 1 + cubes['damage_per_cube']*min(me.get('cubes',0), cubes['stat_cap'])
            distant = all(math.dist(e['pos'],me['pos']) > 100 and not e.get('charging') for e in s.enemies)
            incoming = any(math.dist(b['pos'],me['pos']) < 30 for b in obs.get('projectiles', []))
            if not incoming and distant and (target['kind'] == 'crate' or target.get('hp',1400) > 2*damage):
                fire = [False,False]
        if target['kind'] == 'mech' and not any(fire):
            yaw = guard_yaw(s,yaw,self.config,self.world)
        return [yaw,pitch], fire, reload
