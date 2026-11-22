"""[CHATGPT_ENHANCEMENT_2026-11-21] Official-mechanics NPC cube approach regressions.

Behavioral unit probes only; not a placement simulator. The official 48-match
score remains the only measure of competitive performance.
"""
import copy
import math
import unittest
from types import SimpleNamespace

from test_agent import recording
from agent.policy import Bot
from agent.observation import Observer
from agent.neutral_farm import NeutralFarm
from agent.neutral_collection import safe_neutral_collection_goal


class NeutralCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hello, frames = recording()
        cls.frame = frames[0]

    def setUp(self):
        self.obs = copy.deepcopy(self.frame)
        self.obs.update(
            t=10., mechs=[], projectiles=[], sounds=[], events=[],
            cubes=[], pickups=[], crates=[], drops=[], offer=None
        )
        me = self.obs['self']
        me.update(pos=[0.,0.,0.], hp=me['max_hp'], grounded=True,
                  in_zone=True, cubes=0, energy=100)
        gun = next(w for w in me['weapons'] if w and w['kind']=='gun')
        gun.update(ammo=12,reload=0.,cooldown=0.)
        self.obs['zone'].update(
            center=[0.,0.], next_center=[0.,0.],
            radius=450.,next_radius=300.,
            shrink_start=60.,shrink_end=110.,dps=20.
        )
        self.npc = dict(id=105,kind='npc',pos=[100.,0.,0.],
                        vel=[0.,0.,0.],aim=[0.,0.],hp=350.,max_hp=350.)
        self.obs['mechs']=[self.npc]
        self.world = SimpleNamespace(
            clear=lambda *_: True,
            walkable=lambda *_: True
        )
        self.farm = NeutralFarm(self.world)

    def aim(self):
        s = Observer().parse(self.obs)
        options = self.farm.targets(s)
        return safe_neutral_collection_goal(
            s, options, self.world, self.hello['config']
        )

    def test_drone_gets_standoff_not_direct_chase(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Two-cube target at 100m."""
        waypoint = self.aim()
        self.assertIsNotNone(waypoint)
        self.assertAlmostEqual(waypoint[0],45.)
        self.assertAlmostEqual(waypoint[1],0.)

    def test_never_chase_inside_drone_threat_radius(self):
        self.npc['pos'][0] = 52.
        self.assertIsNone(self.aim())

    def test_preserve_higher_priority_ground_cube(self):
        self.obs['cubes']=[dict(id=5010,pos=[15.,0.,0.])]
        self.assertIsNone(self.aim())

    def test_preserve_imminent_supply_capture(self):
        self.obs['drops'] = [dict(id=20005,pos=[55.,0.,0.],
                                  lands_in=3.,radius=8.,capture_s=4.,
                                  progress=0.,holder=None)]
        self.assertIsNone(self.aim())

    def test_preserve_nearby_weapon_acquisition(self):
        self.obs['self']['weapons'][1]=None
        self.obs['pickups']=[dict(id=8015,kind='laser',pos=[28.,0.,0.])]
        self.assertIsNone(self.aim())

    def test_never_divert_during_enemy_engagement(self):
        self.obs['mechs'].append(dict(id=2,kind='mech',pos=[90.,30.,0.],
                                      vel=[0.,0.,0.],hp=1000.,weapons=['gun']))
        self.assertIsNone(self.aim())

    def test_never_expose_mech_on_low_health_or_low_ammo(self):
        self.obs['self']['hp']=.75*self.obs['self']['max_hp']
        self.assertIsNone(self.aim())
        self.obs['self']['hp']=self.obs['self']['max_hp']
        self.obs['self']['weapons'][0]['ammo']=3
        self.assertIsNone(self.aim())

    def test_maxed_cube_bonus_and_unsafe_zone(self):
        self.obs['self']['cubes']=self.hello['config']['cubes']['stat_cap']
        self.assertIsNone(self.aim())
        self.obs['self']['cubes']=0
        self.obs['zone']['next_radius']=90
        self.assertIsNone(self.aim())

    def test_blocked_first_step_no_unsafe_chase(self):
        self.world.walkable=lambda *_:False
        self.assertIsNone(self.aim())

    def test_recent_hostile_sound_or_projectile_veto(self):
        self.obs['sounds']=[dict(kind='gun',dist='near',bearing=0,age=.1)]
        self.assertIsNone(self.aim())
        self.obs['sounds']=[]
        self.obs['projectiles']=[dict(id=11,kind='gun',pos=[0.,10.,4.],
                                       vel=[0.,-10.,0.])]
        self.assertIsNone(self.aim())

    def test_policy_navigates_toward_standoff_and_keeps_original_fire(self):
        bot=Bot(copy.deepcopy(self.hello))
        bot.world.walkable=lambda *_:True
        bot.world.clear=lambda *_:True
        action=bot.act(self.obs)
        self.assertGreater(action['move'][0],.8)
        self.assertEqual(len(action['fire']),2)
        self.assertNotIn('drop',action)

    def test_policy_still_holds_at_quiet_goal_without_eligible_npc(self):
        bot=Bot(copy.deepcopy(self.hello))
        bot.world.walkable=lambda *_:True
        bot.world.clear=lambda *_:True
        self.obs['mechs']=[]
        self.assertEqual(bot.act(self.obs)['move'],[0.,0.])


if __name__=='__main__':
    unittest.main()
