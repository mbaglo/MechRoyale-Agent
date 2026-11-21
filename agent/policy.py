"""[CODEX_ENHANCEMENT_2026-11-21] Authoritative decision function."""
import math
from .world import World
from .observation import Observer
from .strategy import Strategy
from .navigation import Navigator
from .combat import Combat
from .roof import RoofRefuge


class Bot:
    name = 'MechRoyale-Agent'

    def __init__(self, hello):
        if hello['protocol'] != 'mechfight/1':
            raise ValueError('unsupported protocol')
        self.config = hello['config']
        self.world = World(hello['map']['dir'])
        self.observer, self.strategy = Observer(), Strategy()
        self.navigator = Navigator(self.world)
        self.combat = Combat(self.config,self.world)
        # [CODEX_ENHANCEMENT_2026-11-21] EXP-008 optional map-checked refuge.
        self.roof = RoofRefuge(self.world)
        self.mode = 'balanced'

    def act(self, obs):
        s = self.observer.parse(obs)
        self.mode = self.strategy.choose(s)
        goal = self.strategy.goal(s,self.mode)
        goal = self.roof.goal(s,goal)
        move, boost = self.navigator.move(s,goal,self.mode)
        aim, fire, reload = self.combat.act(s,self.mode)
        action = dict(tick=obs['tick'],move=move,boost=boost,jump=False,aim=aim,fire=fire,reload=reload)
        action = self.roof.apply(s,action)
        offer = obs.get('offer')
        if offer and offer['choices']:
            ranks = {'nanites':100,'armor':95,'plating':90,'servos':85,'reactor':80,'jets':75,
                     'gun_rate':65,'gun_damage':64,'gun_mag':62,'laser_damage':60,'lightning_range':60}
            action['pick'] = max(range(len(offer['choices'])),key=lambda i:ranks.get(offer['choices'][i]['id'],40))
        me = s.me
        held = {w['kind'] for w in me['weapons'] if w}
        nearby = [p for p in obs.get('pickups',[]) if p['kind'] not in held and
                  math.dist(p['pos'][:2],me['pos'][:2]) <= self.config['loot']['pickup_radius'] and abs(p['pos'][2]-me['pos'][2])<=4]
        if nearby and any(w is None for w in me['weapons']):
            action['take'] = min(nearby,key=lambda p:math.dist(p['pos'],me['pos']))['id']
        # Keep serialization strict: a non-finite result is never a legal action.
        if not all(math.isfinite(v) for v in action['move']+action['aim']):
            raise ValueError('non-finite action')
        return action
