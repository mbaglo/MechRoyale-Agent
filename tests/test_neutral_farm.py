"""[CHATGPT_FIX_2026-11-21] Drone-cube acquisition and PvP safety regressions.

The official protocol says NPC drones drop two cubes and have 3.5m height.
The existing bot never targeted those neutral resource opportunities. These
tests validate action choices, NOT simulated game scores or placement.
"""
import copy
import math
import unittest

from test_agent import recording
from agent.combat import Combat
from agent.neutral_farm import NeutralFarm
from agent.observation import Observer


class OpenWorld:
    """[CHATGPT_ENHANCEMENT_2026-11-21] Synthetic unobstructed range test."""
    def clear(self, a, b):
        return True


class ClosedWorld:
    """[CHATGPT_ENHANCEMENT_2026-11-21] Synthetic obstructed shot test."""
    def clear(self, a, b):
        return False


class NeutralFarmTests(unittest.TestCase):
    def setUp(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Official config with a safe synthetic pose."""
        self.hello, frames = recording()
        self.obs = copy.deepcopy(frames[0])
        self.obs.update(t=20., tick=400, events=[], sounds=[],
                        crates=[], projectiles=[], cubes=[], pickups=[], drops=[])
        me = self.obs['self']
        me.update(pos=[0.,0.,0.], vel=[0.,0.,0.], hp=1400.,
                  max_hp=1400., aim=[0.,0.], in_zone=True,
                  grounded=True, energy=100.)
        me['weapons'] = [
            dict(kind='gun', cooldown=0., ammo=12, reload=0.,
                 stats=copy.deepcopy(self.hello['config']['weapons']['gun'])),
            None
        ]
        me['stats']['muzzle_height']=7.
        me['stats']['min_pitch']=-.8
        me['stats']['max_pitch']=1.2
        self.obs['zone'] = dict(center=[0.,0.],radius=560.,
                                next_center=[0.,0.],next_radius=380.,
                                shrink_start=60.,shrink_end=120.,dps=20.)
        self.npc = dict(id=104,kind='npc',pos=[90.,0.,0.],
                        vel=[0.,0.,0.],hp=350.,max_hp=350.,
                        aim=[math.pi,0.],weapons=[])
        self.obs['mechs']=[self.npc]

    def situation(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Parse like the production bot."""
        return Observer().parse(self.obs)

    def test_drone_shot_from_90m_and_actual_npc_height(self):
        """[CHATGPT_FIX_2026-11-21] Farm a clear, healthy, unthreatened drone."""
        situation=self.situation()
        world=OpenWorld()
        combat=Combat(self.hello['config'],world)
        aim,fire,reload=combat.act(situation,'balanced')
        expected=math.atan2(1.75-7.,90.)
        self.assertAlmostEqual(aim[1],expected,places=5)
        self.assertFalse(any(fire))
        self.assertFalse(reload)
        self.obs['self']['aim']=aim
        situation=self.situation()
        _,fire,_=combat.act(situation,'balanced')
        self.assertEqual(fire,[True,False])

    def test_never_farm_while_real_opponent_is_visible(self):
        """[CHATGPT_FIX_2026-11-21] Preserve human-mech combat priority."""
        self.obs['mechs'].append(dict(
            id=6,kind='mech',pos=[35.,0.,0.],vel=[0.,0.,0.],
            hp=1000.,max_hp=1400.,aim=[math.pi,0.],weapons=['gun']))
        combat=Combat(self.hello['config'],OpenWorld())
        combat.act(self.situation(),'balanced')
        self.assertEqual(combat.target_id,6)

    def test_blocked_line_of_fire_cannot_target_npc(self):
        """[CHATGPT_FIX_2026-11-21] No projectiles through opaque cover."""
        farm=NeutralFarm(ClosedWorld())
        self.assertEqual(farm.targets(self.situation()),[])

    def test_nearby_enemy_sound_blocks_farm_for_four_seconds(self):
        """[CHATGPT_FIX_2026-11-21] Preserve survival after a gun warning."""
        farm=NeutralFarm(OpenWorld())
        self.obs['sounds']=[dict(kind='gun',bearing=1.,dist='near',age=.05)]
        self.assertEqual(farm.targets(self.situation()),[])
        self.obs['sounds']=[]
        self.obs['t']=22.
        self.assertEqual(farm.targets(self.situation()),[])
        self.obs['t']=25.
        self.assertEqual(len(farm.targets(self.situation())),1)

    def test_recent_damage_blocks_neutral_engagement(self):
        """[CHATGPT_FIX_2026-11-21] Damage blocks nonessential combat."""
        farm=NeutralFarm(OpenWorld())
        self.obs['events']=[dict(type='damaged',amount=90,weapon='gun',bearing=0.,by=7)]
        self.assertEqual(farm.targets(self.situation()),[])
        self.obs['events']=[]
        self.obs['t']=22.
        self.assertEqual(farm.targets(self.situation()),[])

    def test_incoming_bullet_health_and_zone_veto(self):
        """[CHATGPT_FIX_2026-11-21] Resource farming is always optional."""
        farm=NeutralFarm(OpenWorld())
        self.obs['projectiles']=[dict(kind='gun',pos=[25.,0.,4.],vel=[-200.,0.,0.])]
        self.assertEqual(farm.targets(self.situation()),[])
        self.obs['projectiles']=[]
        self.obs['t']=27.
        self.obs['self']['hp']=700.
        self.assertEqual(farm.targets(self.situation()),[])
        self.obs['self']['hp']=1400.
        self.obs['self']['in_zone']=False
        self.assertEqual(farm.targets(self.situation()),[])

    def test_secondary_weapon_is_not_wasted_on_drone(self):
        """[CHATGPT_FIX_2026-11-21] Preserve mortar for opponent encounters."""
        self.obs['self']['weapons'][1]=dict(
            kind='mortar',cooldown=0.,
            stats=copy.deepcopy(self.hello['config']['weapons']['mortar']))
        combat=Combat(self.hello['config'],OpenWorld())
        aim,fire,_=combat.act(self.situation(),'balanced')
        self.obs['self']['aim']=aim
        _,fire,_=combat.act(self.situation(),'balanced')
        self.assertEqual(fire,[True,False])

    def test_outside_future_zone_and_empty_magazine_veto(self):
        """[CHATGPT_FIX_2026-11-21] No late unsafe target or wasted empty firing."""
        farm=NeutralFarm(OpenWorld())
        self.obs['zone']['next_radius']=50.
        self.assertEqual(farm.targets(self.situation()),[])
        self.obs['zone']['next_radius']=380.
        self.obs['self']['weapons'][0]['ammo']=0
        self.assertEqual(farm.targets(self.situation()),[])


if __name__=='__main__':
    unittest.main()
