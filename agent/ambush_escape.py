"""[CHATGPT_ENHANCEMENT_2026-11-21] Unseen-fire response for a survival-first agent.

Only damage with a reported world-frame bearing can activate this. The aim,
fire, mode and ordinary movement pipelines remain unchanged. This addresses
the baseline's idle-goal behavior when hit by an untracked attacker while
already in the safe circle.

Official protocol: damaged events carry an attacker bearing; movement is
limited by walkable terrain; armor and health are valuable for placement.
This is a bounded directional/geometry heuristic, not a match simulator.
"""
import math


class AmbushEscape:
    """[CHATGPT_ENHANCEMENT_2026-11-21] Plan a short evasive goal after unseen fire."""

    def __init__(self, world):
        self.world = world
        self.until = -float('inf')
        self.bearing = None

    def goal(self, s):
        """[CHATGPT_FIX_2026-11-21] Escape confirmed unseen damage, not noises.

        A nearby visible opponent is already handled by the existing
        movement/combat controllers. Do not displace a supply-capture goal,
        urgent zone traversal, or other normal strategic priorities.
        """
        obs, me = s.obs, s.me
        if s.enemies or s.urgent or not me['in_zone'] or not me.get('grounded',True):
            self.until = -float('inf')
            return None

        impacts = [
            e for e in obs.get('events',())
            if e.get('type') == 'damaged'
            and e.get('weapon') != 'zone'
            and isinstance(e.get('bearing'), (int,float))
            and math.isfinite(e['bearing'])
        ]
        if impacts:
            self.bearing = impacts[-1]['bearing']
            self.until = obs['t'] + 2.2
        if self.bearing is None or obs['t'] >= self.until:
            return None

        pos, stats = me['pos'], me['stats']
        zone = obs['zone']
        # Five nonrandom headings: flee or sidestep. Favor lateral lines
        # behind buildings instead of running through a collision prism.
        away = self.bearing + math.pi
        angle_offsets = (0., -.65, .65, -1.25, 1.25)
        max_distance = min(24., 2.*stats.get('walk_speed',11.7))
        if max_distance < 3.:
            return None
        attacker = [
            pos[0]+55*math.cos(self.bearing),
            pos[1]+55*math.sin(self.bearing),
            pos[2]+stats.get('eye_height',8.)
        ]
        best_goal, best_value = None, -float('inf')
        for distance in (max_distance, max_distance*.55):
            for offset in angle_offsets:
                angle = away+offset
                goal = [pos[0]+distance*math.cos(angle),
                        pos[1]+distance*math.sin(angle)]
                # Avoid running into zone damage for a speculative escape.
                if math.dist(goal, zone['center']) > zone['radius']-8:
                    continue
                end = [goal[0],goal[1],self.world.ground(*goal)]
                if not self.world.walkable(pos,end,stats):
                    continue
                danger_distance = math.dist(goal,attacker[:2])
                goal_head = [goal[0],goal[1],end[2]+stats.get('eye_height',8.)]
                covered = not self.world.clear(attacker,goal_head)
                future_overrun = max(
                    0., math.dist(goal,zone['next_center']) - (zone['next_radius']-10)
                )
                # A covered lateral path beats straight exposed flight;
                # but don't abandon the next circle to avoid hypothetical fire.
                value = danger_distance + (22. if covered else 0.) - 3.*future_overrun
                if value > best_value:
                    best_goal, best_value = goal, value
        return best_goal
