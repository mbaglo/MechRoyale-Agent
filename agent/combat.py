"""[CODEX_ENHANCEMENT_2026-11-21] Intercepts, weapon control and fire discipline."""
import math


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

    def select_weapon(self, weapons, distance, s, target):
        """[CODEX_ENHANCEMENT_2026-11-21] Ready, usable weapons take aim priority."""
        choices = []
        for w in weapons:
            if not w or (w.get('cooldown',0)>.1 and not w.get('charge',0)):
                continue
            kind,st = w['kind'],w['stats']
            score = 0
            if kind=='gun' and w.get('ammo',0)>0 and not w.get('reload',0) and distance<st['range']:
                score = 3
            elif kind=='lightning' and distance<st['range'] and s.me['energy']>st['energy']+30:
                score = 5 if 'laser' in target.get('weapons',[]) else 4
            elif kind=='laser' and distance<st['range'] and (not s.emergency or w.get('charge',0)>0):
                score = 6 if w.get('charge',0)>0 else 4
            elif kind=='mortar' and distance>st['splash_radius']*2+8:
                # A straight-line necessary condition, plus ballistic feasibility
                # checked again against height and pitch before firing.
                if distance < st['speed']**2/st['gravity']*.95:
                    score = 4.5
            if score:
                choices.append((score,w))
        return max(choices,key=lambda pair:pair[0])[1] if choices else None

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
            pressure = (s.threat_weights or {}).get(e['id'],0)
            return d + e.get('hp',1400)*.025 - (15 if e['id'] == self.target_id else 0) - min(2,pressure)*20
        targets.sort(key=priority)
        target = None
        for e in targets[:8]:
            height = {'mech':4.5*(1+.05*e.get('cubes',0)), 'npc':1.75, 'crate':1.2}[e['kind']]
            point = [e['pos'][0],e['pos'][1],e['pos'][2]+height]
            if self.world.clear(origin,point):
                target = e
                break
        reload = any(w and w['kind']=='gun' and w.get('reload',0)==0 and
                     (w.get('ammo',0)==0 or ((not s.enemies or (mode=='conservative' and all(math.dist(e['pos'],me['pos'])>80 for e in s.enemies))) and w.get('ammo',0)<w['stats']['mag']*.6)) for w in me['weapons'])
        if target is None:
            # Face a heard attacker before scanning; preserve front armor.
            bearings = [e['bearing'] for e in obs.get('events',[]) if e['type']=='damaged' and e.get('bearing') is not None]
            sounds = [e for e in obs.get('sounds',[]) if e['kind'] in ('gun','laser_charge','lightning')]
            yaw = bearings[-1] if bearings else sounds[-1]['bearing'] if sounds else obs['t']*.6
            return [angle_delta(yaw,0),0.], [False,False], reload
        self.target_id = target['id']
        height = 1.2 if target['kind']=='crate' else 4.5*(1+.05*target.get('cubes',0))
        point = [target['pos'][0], target['pos'][1], target['pos'][2]+height]
        distance = math.dist(origin,point)
        weapons = me['weapons']
        # A ready/charging secondary takes aim priority; gun otherwise.
        # [CODEX_FIX_2026-11-21] A reloading gun or unusable secondary must
        # not displace an available weapon's aim solution.
        selected = self.select_weapon(weapons,distance,s,target)
        selected = selected or next((w for w in weapons if w), None)
        aim_point = point
        pitch = None
        if selected and selected['kind']=='gun':
            aim_point = intercept(origin, point, target.get('vel',[0,0,0]), selected['stats']['speed'])
        elif selected and selected['kind']=='mortar':
            st = selected['stats']
            # [CODEX_FIX_2026-11-21] Mortar tube is above the gun muzzle.
            origin[2] = me['pos'][2]+me['stats'].get('height',9)+.5
            aim_point = intercept(origin,point,target.get('vel',[0,0,0]),st['speed'])
            r = math.dist(origin[:2],aim_point[:2]); dz = aim_point[2]-origin[2]
            v, g = st['speed'], st['gravity']
            discriminant = v**4-g*(g*r*r+2*dz*v*v)
            if discriminant >= 0 and r > 1:
                pitch = math.atan((v*v-math.sqrt(discriminant))/(g*r))
        yaw = math.atan2(aim_point[1]-origin[1],aim_point[0]-origin[0])
        pitch = pitch if pitch is not None else math.atan2(aim_point[2]-origin[2],math.dist(origin[:2],aim_point[:2]))
        feasible_pitch = me['stats']['min_pitch'] <= pitch <= me['stats']['max_pitch']
        pitch = max(me['stats']['min_pitch'],min(me['stats']['max_pitch'],pitch))
        aligned = abs(angle_delta(yaw,me['aim'][0])) < math.atan2(2,max(distance,1))+.015 and abs(pitch-me['aim'][1]) < .04
        # [CODEX_ENHANCEMENT_2026-11-21] Retain close defensive shots while
        # suppressing distant engagements during an emergency or recovery.
        retreat = mode=='conservative' and distance > (40 if s.emergency else 55)
        fire = [False,False]
        for i,w in enumerate(weapons):
            if not w:
                continue
            kind, st = w['kind'], w['stats']
            allowed = aligned and not retreat and w.get('cooldown',0)<=.1
            if kind=='gun':
                # Do not fire the gun along the mortar's elevated trajectory.
                fire[i] = allowed and distance < st['range'] and w.get('ammo',0)>0 and not w.get('reload',0) and (selected is None or selected['kind']!='mortar')
                # [CODEX_FIX_2026-11-21] A direct laser/lightning aim may not
                # lead enough for the gun. Check its own intercept before firing.
                gun_origin = [me['pos'][0],me['pos'][1],me['pos'][2]+me['stats']['muzzle_height']]
                predicted = intercept(gun_origin,point,target.get('vel',[0,0,0]),st['speed'])
                gun_yaw = math.atan2(predicted[1]-gun_origin[1],predicted[0]-gun_origin[0])
                gun_pitch = math.atan2(predicted[2]-gun_origin[2],math.dist(predicted[:2],gun_origin[:2]))
                gun_ok = abs(angle_delta(gun_yaw,me['aim'][0]))<math.atan2(2,max(distance,1))+.015 and abs(gun_pitch-me['aim'][1])<.04
                fire[i] = bool(fire[i] and gun_ok and self.world.clear(gun_origin,predicted))
            elif kind=='lightning':
                reserve = min(me.get('max_energy',100)*.7,30+s.pressure*6+(10 if s.health<.45 else 0))
                fire[i] = bool(not retreat and distance < st['range'] and me['energy'] > st['energy']+reserve and abs(angle_delta(yaw,me['aim'][0])) < math.radians(st['cone_deg'])*.45 and w.get('cooldown',0)<=.1)
            elif kind=='laser':
                charge = w.get('charge',0)
                fire[i] = bool(not retreat and (not s.emergency or charge>0) and distance < st['range'] and w.get('cooldown',0)<=.1 and
                               (charge < st['charge'] or not aligned))
            elif kind=='mortar':
                r = math.dist(origin[:2],aim_point[:2]); dz = aim_point[2]-origin[2]
                possible = st['speed']**4-st['gravity']*(st['gravity']*r*r+2*dz*st['speed']**2)>=0
                fire[i] = bool(allowed and selected is w and possible and feasible_pitch and distance > st['splash_radius']*2+8)
                if fire[i]:
                    # [CODEX_ENHANCEMENT_2026-11-21] Verify the shell arc; a
                    # clear direct ray does not mean the ballistic path is clear.
                    speed,gravity = st['speed'],st['gravity']
                    flight = r/max(1,speed*math.cos(pitch))
                    for sample in range(1,33):
                        t = flight*sample/32
                        x = origin[0]+speed*math.cos(pitch)*math.cos(yaw)*t
                        y = origin[1]+speed*math.cos(pitch)*math.sin(yaw)*t
                        z = origin[2]+speed*math.sin(pitch)*t-gravity*t*t/2
                        if self.world.solid(x,y,z) or z<self.world.ground(x,y):
                            fire[i] = False
                            break
        return [yaw,pitch], fire, reload
