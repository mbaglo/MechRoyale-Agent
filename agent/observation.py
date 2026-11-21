"""[CODEX_ENHANCEMENT_2026-11-21] Observation interpretation and bounded state."""
import math
from dataclasses import dataclass
from .tuning import DEFAULT


@dataclass
class Situation:
    obs: dict
    me: dict
    enemies: list
    health: float
    damage: float
    urgent: bool
    pressure: float = 0.0
    crossfire: float = 0.0
    pursuing: int = 0
    escape_routes: tuple = ()
    escape_fraction: float = 1.0
    threat_weights: dict = None
    emergency: bool = False
    phase: str = 'early'
    zone_distance: float = 0.0
    recent_damage: float = 0.0


class Observer:
    def __init__(self, world=None, tuning=DEFAULT):
        self.last_damage = -100.0
        self.tracks = {}
        self.world, self.tuning = world, tuning
        self.damage_history = []

    def parse(self, obs):
        me = obs['self']
        damage = sum(e.get('amount', 0) for e in obs.get('events', []) if e['type'] == 'damaged')
        if damage:
            self.last_damage = obs['t']
            self.damage_history.append((obs['t'], damage))
        self.damage_history = [(t,d) for t,d in self.damage_history if obs['t']-t <= self.tuning.damage_window]
        enemies = sorted((m for m in obs.get('mechs', []) if m['kind'] == 'mech'),
                         key=lambda m: math.dist(m['pos'], me['pos']))
        for e in enemies:
            self.tracks[e['id']] = (obs['t'], e)
        self.tracks = {k:v for k,v in self.tracks.items() if obs['t']-v[0] < 6}
        z = obs['zone']
        dist = math.dist(me['pos'][:2], z['next_center'])
        travel = max(0, dist-z['next_radius']+15)/max(1, me['stats']['walk_speed'])
        # [CODEX_FIX_2026-11-21] Allow a detour, and start travel before shrink.
        remaining = max(0, dist-z['next_radius']+15)
        urgent = not me['in_zone'] or (remaining > 0 and obs['t']+travel*1.45+12 >= z['shrink_end'])
        s = Situation(obs, me, enemies, me['hp']/max(1,me['max_hp']), damage, urgent)
        s.zone_distance = remaining
        s.phase = 'late' if z['radius'] <= 100 or obs.get('alive',16) <= 4 else 'mid' if obs['t'] >= 110 else 'early'
        self.assess(s)
        return s

    def assess(self, s):
        """[CODEX_ENHANCEMENT_2026-11-21] Pressure uses observable intent, not squad assumptions."""
        me, pos, cfg = s.me, s.me['pos'], self.tuning
        weights, bearings = {}, []
        attackers = {e.get('by') for e in s.obs.get('events',[]) if e['type']=='damaged'}
        for e in s.enemies:
            dx, dy = pos[0]-e['pos'][0], pos[1]-e['pos'][1]
            d = max(1,math.hypot(dx,dy))
            velocity = e.get('vel',[0,0,0])
            approach = max(0,(velocity[0]*dx+velocity[1]*dy)/d)
            facing = math.cos(e['aim'][0]-math.atan2(dy,dx)) > .85
            near = max(0,1-d/cfg.threat_distance)
            weight = near*(.25+cfg.approach_weight*min(1,approach/8)+cfg.facing_weight*facing)
            kinds = e.get('weapons',[])
            if 'lightning' in kinds and d < 55:
                weight += .8
            if e.get('charging') and facing:
                weight += .9
            if 'mortar' in kinds and 25 < d < 220 and facing:
                weight += .25
            if e['id'] in attackers:
                weight += 1
            weights[e['id']] = weight
            if near and (approach > 2 or facing or e['id'] in attackers):
                s.pursuing += 1
                bearings.append(math.atan2(-dy,-dx))
        if len(bearings) > 1:
            s.crossfire = 1-math.hypot(sum(math.cos(b) for b in bearings),sum(math.sin(b) for b in bearings))/len(bearings)
        routes = []
        if self.world:
            z = s.obs['zone']
            for i in range(8):
                dx,dy = math.cos(i*math.pi/4),math.sin(i*math.pi/4)
                end = [pos[0]+dx*cfg.escape_probe,pos[1]+dy*cfg.escape_probe,pos[2]]
                # Outside the circle, allow only routes that reduce zone exposure.
                before = math.dist(pos[:2],z['center'])
                after = math.dist(end[:2],z['center'])
                zone_ok = after < z['radius']-3 or after < before
                if zone_ok and self.world.walkable(pos,end,me['stats']):
                    routes.append((dx,dy))
            s.escape_routes = tuple(routes)
            s.escape_fraction = len(routes)/8
        s.threat_weights = weights
        s.recent_damage = sum(d for _,d in self.damage_history)
        active = sum(weights.values())
        s.pressure = (active + s.crossfire*cfg.crossfire_weight + s.recent_damage/max(1,me['max_hp'])*cfg.damage_weight)
        if active > .5:
            s.pressure += (1-s.escape_fraction)*cfg.trapped_weight
            s.pressure += max(0,1-me['energy']/30)*cfg.low_energy_weight
        s.emergency = (s.pressure >= cfg.emergency_pressure or
                       (s.health < .3 and (s.pursuing > 0 or s.recent_damage > 0)) or
                       (s.pursuing >= 2 and (s.crossfire > .4 or s.escape_fraction < .3)))
