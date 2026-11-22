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
    # [ASTRA_ENHANCEMENT_2026-11-21] Recovery is available after a quiet interval in the zone.
    recovery_window: bool = False


class Observer:
    def __init__(self):
        self.last_damage = -100.0
        self.tracks = {}
        self.last_exchange = None
        self.previous_hp = None
        self.was_in_zone = False

    def parse(self, obs):
        me = obs['self']
        damage = sum(e.get('amount', 0) for e in obs.get('events', []) if e['type'] == 'damaged')
        if damage:
            self.last_damage = obs['t']
        # [ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
        # Both outgoing damage and arriving from the zone restart the healing clock.
        lost_hp = self.previous_hp is not None and me['hp'] < self.previous_hp
        if (self.last_exchange is None or damage or lost_hp or not self.was_in_zone or not me['in_zone'] or
                any(e['type'] == 'hit' for e in obs.get('events', []))):
            self.last_exchange = obs['t']
        self.previous_hp = me['hp']
        self.was_in_zone = me['in_zone']
        enemies = sorted((m for m in obs.get('mechs', []) if m['kind'] == 'mech'),
                         key=lambda m: math.dist(m['pos'], me['pos']))
        for e in enemies:
            self.tracks[e['id']] = (obs['t'], e)
        self.tracks = {k:v for k,v in self.tracks.items() if obs['t']-v[0] < 6}
        z = obs['zone']
        dist = math.dist(me['pos'][:2], z['next_center'])
        travel = max(0, dist-z['next_radius']+15)/max(1, me['stats']['walk_speed'])
        # [ASTRA_FIX_2026-11-21] [CODEX_FIX_2026-11-21] A mech already inside
        # the future safety margin has no remaining trip before this deadline.
        urgent = not me['in_zone'] or (travel > 0 and obs['t']+travel+8 >= z['shrink_end'])
        health = me['hp']/max(1,me['max_hp'])
        recovery_window = (me['in_zone'] and health < .8 and
                           obs['t'] - self.last_exchange >= me['stats']['regen_delay'] - .5)
        return Situation(obs, me, enemies, health, damage, urgent, recovery_window)
