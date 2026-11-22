"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Check whether a brief finishing volley is plausible while a second nearby mech is screened.
"""
import math


def isolated_finish(s, close, world, config):
    me=s.me
    if (len(close)!=2 or len(s.enemies)!=2 or s.health<.6 or me['energy']<me['stats']['boost_drain'] or s.damage or s.urgent or
            any(e.get('charging') for e in close)):
        return False
    gun=next((w for w in me['weapons'] if w and w['kind']=='gun' and not w.get('reload',0)),None)
    if not gun:
        return False
    a,b=sorted(close,key=lambda e:e.get('hp',math.inf))
    spec=gun['stats']
    cubes=config['cubes']
    dmg=spec['damage']*(1+cubes['damage_per_cube']*min(me['cubes'],cubes['stat_cap']))
    if not 0<a.get('hp',math.inf)<=max(0,gun['ammo']-1)*dmg:
        return False
    shots=math.ceil(a['hp']/dmg)
    p,ep=me['pos'],a['pos']
    bearing=math.atan2(ep[1]-p[1],ep[0]-p[0])
    slew=abs((bearing-me['aim'][0]+math.pi)%(2*math.pi)-math.pi)/me['stats']['turn_rate']
    time=max(slew,gun.get('cooldown',0))+(shots-1)*spec['cooldown']+math.dist(ep,p)/spec['speed']+.15
    if time>spec['reload']:
        return False
    muzzle=[*p[:2],p[2]+me['stats']['muzzle_height']]
    scale=1+cubes['size_per_cube']*a.get('cubes',0)
    if not world.clear(muzzle,[*ep[:2],ep[2]+.5*config['mech']['height']*scale]):
        return False
    # Test present visibility and short reachable movements around the screened mech.
    q=b['pos']
    size=1+cubes['size_per_cube']*b.get('cubes',0)
    body=[*p[:2],p[2]+.5*me['stats']['height']]
    top=[*p[:2],p[2]+.95*me['stats']['height']]
    def threatens(site):
        eye=[*site[:2],site[2]+config['mech']['muzzle_height']*size]
        return world.clear(eye,body) or world.clear(eye,top)
    if threatens(q):
        return False
    rival_stats=dict(config['mech'],radius=config['mech']['radius']*size,height=config['mech']['height']*size)
    if abs(q[2]-world.ground(*q[:2]))>rival_stats['step_up']:
        return False
    reach=time*max(rival_stats['boost_speed'],math.hypot(*b.get('vel',[0,0])[:2]))
    if math.dist(p[:2],q[:2])<reach+config['vision']['near_range']:
        return False
    angle=math.atan2(p[1]-q[1],p[0]-q[0])
    for dist in (.5*reach,reach):
        for side in (0,.25,-.25,.5,-.5):
            x=q[0]+dist*math.cos(angle+side*math.pi)
            y=q[1]+dist*math.sin(angle+side*math.pi)
            site=[x,y,world.ground(x,y)]
            if world.walkable(q,site,rival_stats) and threatens(site):
                return False
    return True
