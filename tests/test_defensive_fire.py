"""[CODEX_ENHANCEMENT_2026-11-21] EXP-003 gun retaliation regressions."""
import copy
import math
from types import SimpleNamespace
import unittest
from test_agent import recording
from agent.observation import Observer
from agent.combat import Combat


class DefensiveFireTests(unittest.TestCase):
    def setUp(self):
        hello, observations = recording()
        self.obs = copy.deepcopy(observations[0])
        self.obs.update(t=10,events=[],sounds=[],mechs=[],crates=[])
        self.obs['self'].update(pos=[0,0,0],aim=[0,math.atan2(-2.5,100)],hp=200)
        self.obs['self']['weapons'] = [dict(kind='gun',cooldown=0,ammo=12,reload=0,stats=hello['config']['weapons']['gun']),None]
        self.obs['mechs'] = [dict(id=5,kind='mech',pos=[100,0,0],vel=[0,0,0],aim=[math.pi,0],hp=1400,max_hp=1400)]
        self.observer = Observer()
        self.combat = Combat(hello['config'],SimpleNamespace(clear=lambda a,b:True))

    def damage(self,by=5,weapon='gun'):
        self.obs['events'] = [dict(type='damaged',by=by,weapon=weapon,amount=45,bearing=0)]

    def act(self):
        return self.combat.act(self.observer.parse(self.obs),'conservative')

    def test_quiet_retreat_still_does_not_fire(self):
        self.assertEqual(self.act()[1],[False,False])

    def test_aligned_recent_attacker_can_receive_gun_fire(self):
        self.damage()
        self.assertTrue(self.act()[1][0])
        self.obs['events'] = []
        self.obs['t'] += .3
        self.assertTrue(self.act()[1][0])
        self.obs['t'] += .4
        self.assertFalse(self.act()[1][0])

    def test_other_enemy_and_zone_damage_do_not_enable_fire(self):
        self.damage(by=6)
        self.assertFalse(self.act()[1][0])
        self.damage(by=None,weapon='zone')
        self.assertFalse(self.act()[1][0])

    def test_alignment_range_ammo_and_reload_still_gate_fire(self):
        self.damage()
        self.obs['self']['aim'] = [math.pi,0]
        self.assertFalse(self.act()[1][0])
        self.obs['self']['aim'] = [0,math.atan2(-2.5,100)]
        gun = self.obs['self']['weapons'][0]
        for field,value in [('ammo',0),('reload',1),('cooldown',1)]:
            old = gun[field]
            gun[field] = value
            self.assertFalse(self.act()[1][0])
            gun[field] = old
        self.obs['mechs'][0]['pos'][0] = 300
        self.assertFalse(self.act()[1][0])

    def test_cover_still_blocks_retaliation(self):
        self.damage()
        self.combat.world.clear = lambda a,b:False
        self.assertEqual(self.act()[1],[False,False])

    def test_expired_attackers_are_removed(self):
        self.damage()
        self.act()
        self.obs['events'] = []
        self.obs['t'] += 2
        self.act()
        self.assertEqual(self.combat.recent_attackers,{})


if __name__ == '__main__':
    unittest.main()
