"""[ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
Recognize a partial-magazine reload opportunity during an observed break in sight.
"""
import math


class ReloadWindow:
    def __init__(self, world, config):
        self.world,self.config=world,config
        self.enemy_id=None
        self.since=0.
        self.last=-math.inf

    def can_reload(self,s,target):
        me=s.me
        gun=next((w for w in me['weapons'] if w and w['kind']=='gun'),None)
        if (target is not None or len(s.enemies)!=1 or s.urgent or s.damage or gun is None or
                gun.get('reload',0)>0 or not 0<gun.get('ammo',0)<=gun['stats']['mag']/2):
            self.enemy_id=None
            return False
        e=s.enemies[0]
        if e.get('charging') or math.dist(e['pos'],me['pos'])<=self.config['vision']['near_range']:
            self.enemy_id=None
            return False
        muzzle=self.config['mech']['muzzle_height']*(1+self.config['cubes']['size_per_cube']*e.get('cubes',0))
        def covered(dt):
            src=[e['pos'][k]+dt*e['vel'][k] for k in range(3)]
            src[2]+=muzzle
            pos=[me['pos'][k]+dt*me['vel'][k] for k in range(3)]
            return all(not self.world.clear(src,[*pos[:2],pos[2]+frac*me['stats']['height']]) for frac in (.5,.95))
        now=s.obs['t']
        if not covered(0):
            self.enemy_id=None
            return False
        if self.enemy_id!=e['id'] or now-self.last>.25:
            self.since=now
        self.enemy_id,self.last=e['id'],now
        # Screen out brief occlusions and an opponent already moving back into view.
        return now-self.since>=.35 and covered(min(1.2,gun['stats']['reload']/2))
