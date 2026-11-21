"""[CODEX_ENHANCEMENT_2026-11-21] Observation interpretation and bounded state."""
import math
from dataclasses import dataclass


@dataclass
class Situation:
    obs: dict
    me: dict
    enemies: list
    health: float
    damage: float
    urgent: bool
    # [ASTRA_ENHANCEMENT_2026-11-21] Observed crate on the current equipment route.
    equipment_crate: int | None = None


class Observer:
    def __init__(self):
        self.last_damage = -100.0
        self.tracks = {}

    def parse(self, obs):
        me = obs['self']
        damage = sum(e.get('amount', 0) for e in obs.get('events', []) if e['type'] == 'damaged')
        if damage:
            self.last_damage = obs['t']
        enemies = sorted((m for m in obs.get('mechs', []) if m['kind'] == 'mech'),
                         key=lambda m: math.dist(m['pos'], me['pos']))
        for e in enemies:
            self.tracks[e['id']] = (obs['t'], e)
        self.tracks = {k:v for k,v in self.tracks.items() if obs['t']-v[0] < 6}
        z = obs['zone']
        dist = math.dist(me['pos'][:2], z['next_center'])
        travel = max(0, dist-z['next_radius']+15)/max(1, me['stats']['walk_speed'])
        urgent = not me['in_zone'] or obs['t']+travel+8 >= z['shrink_end']
        return Situation(obs, me, enemies, me['hp']/max(1,me['max_hp']), damage, urgent)
