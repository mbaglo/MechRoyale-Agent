"""[CODEX_ENHANCEMENT_2026-11-21] Burst boosting with recovery hysteresis."""
import math
from .tuning import DEFAULT


class EnergyPolicy:
    def __init__(self, tuning=DEFAULT):
        self.tuning = tuning
        self.recovering = False
        self.reserve = 30.

    def boost(self, s, move, projectile_danger=False):
        me, st = s.me, s.me['stats']
        capacity = me.get('max_energy',100)
        drain = st.get('boost_drain',17)
        seconds = self.tuning.reserve_seconds + min(4,s.pressure)*self.tuning.reserve_pressure_seconds
        seconds += .8 if s.health < .45 else 0
        # Reserve an additional burst when safety requires a long zone crossing.
        # Sustainable travel still walks during recovery; this is not an estimate
        # that the entire trip can be boosted on one energy bar.
        seconds += min(1,s.zone_distance/max(1,st.get('boost_speed',19.5)*4))
        self.reserve = min(capacity*.75, drain*seconds)
        energy = me['energy']
        # [CODEX_FIX_2026-11-21] No airborne jet merely because enemies exist.
        if not me.get('grounded',True) or math.hypot(*move) < .1:
            return False
        emergency = s.emergency or projectile_danger or not me['in_zone']
        if emergency:
            self.recovering = energy < drain*.15
            return energy >= drain*.15
        if energy <= self.reserve:
            self.recovering = True
        if self.recovering and energy >= min(capacity*.95,self.reserve+drain*1.2):
            self.recovering = False
        need = s.urgent or (s.pursuing > 0 and s.pressure > 1.0)
        return bool(need and not self.recovering and energy > self.reserve)
