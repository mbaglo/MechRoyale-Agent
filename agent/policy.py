"""[CODEX_ENHANCEMENT_2026-11-21] Authoritative decision function."""
import math
from .world import World
from .observation import Observer
from .strategy import Strategy
from .navigation import Navigator
from .combat import Combat
from .zone_route import ZoneRoute
from .supply import finishing_drop, stay_inside
from .recovery_cover import RecoveryCover  # [CHATGPT_ENHANCEMENT_2026-11-21]


class Bot:
    name = 'MechRoyale-Agent'

    def __init__(self, hello):
        if hello['protocol'] != 'mechfight/1':
            raise ValueError('unsupported protocol')
        self.config = hello['config']
        self.world = World(hello['map']['dir'])
        self.observer, self.strategy = Observer(), Strategy()
        self.navigator = Navigator(self.world)
        self.zone_route = ZoneRoute(self.world)
        # [CHATGPT_ENHANCEMENT_2026-11-21] Restore separately verified shelter behavior.
        self.recovery_cover = RecoveryCover(self.world, self.config)
        self.combat = Combat(self.config,self.world)
        self.mode = 'balanced'

    def act(self, obs):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Combine 2.92 supply priority with
        earlier 2.81 recovery cover. Preserve original goal, navigation, combat,
        upgrades, pickups and schema safety. No changes to opponent behavior.
        """
        s = self.observer.parse(obs)
        self.mode = self.strategy.choose(s)

        # Preserve EXP-031 supply capture and the validated route planner.
        drop = finishing_drop(s, self.config)
        goal = drop['pos'][:2] if drop else self.strategy.goal(s, self.mode)
        goal = self.zone_route.waypoint(s, goal)

        # [CHATGPT_FIX_2026-11-21] Capture takes priority over recovery
        # shelter, preventing a nearly completed supply drop from being lost.
        shelter, hold = None, False
        if drop is not None:
            self.recovery_cover.reset()
        else:
            # Reuse the independently scored RecoveryCover policy: it only
            # selects walkable ground shelter during a safe regeneration window.
            shelter, hold = self.recovery_cover.route(s)

        if hold:
            self.navigator.previous = (0., 0.)
            move, boost = [0., 0.], False
        else:
            destination = shelter if shelter is not None else goal
            # [CHATGPT_FIX_2026-11-21] A zone-path detour and an alternate
            # shelter destination must not share the zone-detour override.
            move, boost = self.navigator.move(
                s, destination, self.mode,
                zone_detour=bool(self.zone_route.path) and shelter is None
            )
            if drop is not None:
                move, boost = stay_inside(s, drop, move, boost, self.world)

        aim, fire, reload = self.combat.act(s, self.mode)
        action = dict(
            tick=obs['tick'], move=move, boost=boost, jump=False,
            aim=aim, fire=fire, reload=reload
        )
        offer = obs.get('offer')
        if offer and offer['choices']:
            ranks = {
                'nanites':100, 'armor':95, 'plating':90, 'servos':85,
                'reactor':80, 'jets':75,
                # [CODEX_ENHANCEMENT_2026-11-21] EXP-011: magazine preference.
                'gun_rate':65, 'gun_damage':64, 'gun_mag':115,
                'laser_damage':60, 'lightning_range':60
            }
            action['pick'] = max(
                range(len(offer['choices'])),
                key=lambda i: ranks.get(offer['choices'][i]['id'], 40)
            )
        me = s.me
        held = {w['kind'] for w in me['weapons'] if w}
        nearby = [
            p for p in obs.get('pickups', [])
            if p['kind'] not in held
            and math.dist(p['pos'][:2], me['pos'][:2])
                <= self.config['loot']['pickup_radius']
            and abs(p['pos'][2] - me['pos'][2]) <= 4
        ]
        if nearby and any(w is None for w in me['weapons']):
            action['take'] = min(
                nearby, key=lambda p: math.dist(p['pos'], me['pos'])
            )['id']
        # Preserve strict serialization and action validity.
        if not all(math.isfinite(v) for v in action['move'] + action['aim']):
            raise ValueError('non-finite action')
        return action
