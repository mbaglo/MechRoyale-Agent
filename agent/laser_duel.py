"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Use adjacent firing and sheltered positions during a confirmed game laser cycle.
"""
import math


class LaserDuel:
    offsets = [(r*math.cos(k*math.pi/4),r*math.sin(k*math.pi/4))
               for r in (4,8,12,16) for k in range(8)]

    def __init__(self, world, config):
        self.world = world
        self.config = config
        self.opponent = None
        self.shot = -math.inf
        self.pair = None
        self.retry = -math.inf

    def plan(self, pos, stats, zone, muzzle, target):
        open_sites, shelters = [],[]
        for dx,dy in [(0,0),*self.offsets]:
            x,y = pos[0]+dx,pos[1]+dy
            site=[x,y,self.world.ground(x,y)]
            if math.dist(site[:2],zone['center'])+5>=zone['radius'] or not self.world.walkable(pos,site,stats):
                continue
            if self.world.clear([x,y,site[2]+stats['muzzle_height']],target):
                open_sites.append(site)
            elif self.sheltered(muzzle,site,stats):
                shelters.append(site)
        best,best_cost = None,math.inf
        for peek in open_sites:
            for hide in shelters:
                step = math.dist(peek[:2],hide[:2])
                if not 1 <= step <= 6:
                    continue
                cost = min(math.dist(pos[:2],peek[:2]),math.dist(pos[:2],hide[:2]))+step
                if cost<best_cost and self.world.walkable(peek,hide,stats):
                    best,best_cost = (peek,hide),cost
        return best

    def sheltered(self, muzzle, site, stats):
        return all(not self.world.clear(muzzle,[*site[:2],site[2]+f*stats['height']]) for f in (.5,.9))

    def goal(self, s):
        me,o = s.me,s.obs
        if len(s.enemies)!=1 or s.urgent or not me['grounded']:
            self.pair = None
            return None
        e=s.enemies[0]
        now=o['t']
        if e['id']!=self.opponent:
            self.opponent,self.shot,self.pair,self.retry = e['id'],-math.inf,None,-math.inf
        arms = [w for w in me['weapons'] if w]
        if 'laser' not in e.get('weapons',[]) or len(arms)!=1 or arms[0]['kind']!='gun':
            return None
        for b in o.get('beams',[]):
            if b['by']==e['id'] and b['kind']=='laser':
                self.shot=max(self.shot,now-b.get('age',0))
        if any(ev['type']=='damaged' and ev.get('weapon')=='laser' and ev.get('by')==e['id']
               for ev in o.get('events',[])) and now-self.shot>.2:
            self.shot=now
        weapon=self.config['weapons']['laser']
        elapsed=now-self.shot
        if not e.get('charging') and elapsed>weapon['cooldown']+weapon['charge']+.6:
            self.pair=None
            return None
        pos,stats,ep=me['pos'],me['stats'],e['pos']
        gap=math.dist(pos[:2],ep[:2])
        if not 60<gap<arms[0]['stats']['range'] or abs(pos[2]-self.world.ground(*pos[:2]))>stats['step_up']:
            return None
        if any(d.get('holder')==me['id'] for d in o.get('drops',[])):
            return None
        scale=1+self.config['cubes']['size_per_cube']*e.get('cubes',0)
        muzzle=[*ep[:2],ep[2]+scale*self.config['mech']['muzzle_height']]
        target=[*ep[:2],ep[2]+.5*scale*self.config['mech']['height']]
        if self.pair:
            peek,hide=self.pair
            if (math.dist(pos[:2],hide[:2])>22 or not self.sheltered(muzzle,hide,stats) or
                    not self.world.clear([*peek[:2],peek[2]+stats['muzzle_height']],target)):
                self.pair=None
        if not self.pair and now>=self.retry:
            self.retry=now+.6
            self.pair=self.plan(pos,stats,o['zone'],muzzle,target)
        if not self.pair:
            return None
        peek,hide=self.pair
        retreat_time=math.dist(peek[:2],hide[:2])/stats['walk_speed']+.25
        safe_to_peek=(not e.get('charging') and elapsed+retreat_time<weapon['cooldown']
                      and arms[0].get('reload',0)<.2 and arms[0].get('ammo',0)>0)
        return (peek if safe_to_peek else hide)[:2]
