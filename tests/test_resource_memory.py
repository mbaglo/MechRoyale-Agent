"""[CHATGPT_FIX_2026-11-21] Observed resource-memory regression tests.

Only policy choices are tested. The official kit supplies no full-game
simulator; these tests do not predict the official placement score.
"""
import copy
import unittest

from test_agent import recording
from agent.observation import Observer
from agent.strategy import Strategy


class ResourceMemoryTests(unittest.TestCase):
    """[CHATGPT_ENHANCEMENT_2026-11-21] Official observation, synthetic FOV-loss cases."""

    def setUp(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Reuse the official recording's configuration."""
        _, frames = recording()
        self.obs = copy.deepcopy(frames[0])
        self.obs.update(t=10., tick=200, mechs=[], events=[], sounds=[],
                        projectiles=[], pickups=[], cubes=[], drops=[], crates=[])
        me = self.obs['self']
        me.update(pos=[0.,0.,0.],vel=[0.,0.,0.],hp=1400.,
                  max_hp=1400.,grounded=True,in_zone=True)
        self.obs['zone'] = dict(center=[0.,0.],radius=500.,
                                next_center=[0.,0.],next_radius=300.,
                                shrink_start=60.,shrink_end=110.,dps=20.)
        self.strategy = Strategy()
        self.observer = Observer()

    def goal(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Use the production observation path."""
        return self.strategy.goal(self.observer.parse(self.obs),'balanced')

    def test_continue_pursuing_last_seen_cube_after_fov_loss(self):
        """[CHATGPT_FIX_2026-11-21] Do not abort an observed route on one blind frame."""
        self.obs['cubes'] = [dict(id=5001,pos=[75.,0.,0.])]
        self.assertEqual(self.goal(),[75.,0.])
        self.obs['cubes'] = []
        self.obs['t'] = 10.1
        self.assertEqual(self.goal(),[75.,0.])
        self.obs['t'] = 12.6
        self.assertEqual(self.goal(),[0.,0.])

    def test_visible_nearby_cube_wins_over_remembered_one(self):
        """[CHATGPT_FIX_2026-11-21] Fresh observations retain original priority."""
        self.obs['cubes']=[dict(id=5001,pos=[75.,0.,0.])]
        self.goal()
        self.obs['cubes']=[dict(id=5002,pos=[10.,0.,0.])]
        self.obs['t']=10.2
        self.assertEqual(self.goal(),[10.,0.])

    def test_discard_missing_pickup_when_close_to_old_location(self):
        """[CHATGPT_FIX_2026-11-21] Don't keep trying to collect absent loot."""
        self.obs['pickups']=[dict(id=8010,kind='laser',pos=[45.,0.,0.])]
        self.assertEqual(self.goal(),[45.,0.])
        self.obs['pickups']=[]
        self.obs['self']['pos']=[39.,0.,0.]
        self.obs['t']=10.2
        self.assertEqual(self.goal(),[0.,0.])

    def test_never_pursue_memory_in_zone_emergency_or_threat(self):
        """[CHATGPT_FIX_2026-11-21] Memory never overrides urgent navigation."""
        self.obs['cubes']=[dict(id=5001,pos=[75.,0.,0.])]
        self.goal()
        self.obs['cubes']=[]
        self.obs['t']=10.2
        self.obs['self']['in_zone']=False
        self.assertEqual(self.goal(),[0.,0.])
        self.obs['self']['in_zone']=True
        self.obs['mechs']=[dict(kind='mech',id=2,pos=[40.,0.,0.],
                               vel=[0.,0.,0.],aim=[3.,0.],hp=900.,weapons=['gun'])]
        self.assertEqual(self.goal(),[0.,0.])
        self.obs['mechs']=[]
        self.obs['self']['hp']=600.
        self.assertEqual(self.goal(),[0.,0.])

    def test_hostile_bullet_and_near_gun_sound_veto_memory(self):
        """[CHATGPT_FIX_2026-11-21] Preserve threat avoidance before loot."""
        self.obs['cubes']=[dict(id=5001,pos=[75.,0.,0.])]
        self.goal()
        self.obs['cubes']=[]
        self.obs['t']=10.2
        self.obs['projectiles']=[dict(pos=[30.,0.,5.],vel=[-220.,0.,0.])]
        self.assertEqual(self.goal(),[0.,0.])
        self.obs['projectiles']=[]
        self.obs['sounds']=[dict(kind='gun',dist='near',bearing=0.)]
        self.assertEqual(self.goal(),[0.,0.])

    def test_respect_future_zone_and_inventory_with_memory(self):
        """[CHATGPT_FIX_2026-11-21] Original filters govern remembered resources."""
        self.obs['pickups']=[dict(id=8010,kind='laser',pos=[80.,0.,0.])]
        self.assertEqual(self.goal(),[80.,0.])
        self.obs['pickups']=[]
        self.obs['t']=10.2
        self.obs['zone']['next_radius']=70.
        self.assertEqual(self.goal(),[0.,0.])
        self.obs['zone']['next_radius']=300.
        self.obs['self']['weapons'][1]=dict(kind='laser',stats={})
        self.assertEqual(self.goal(),[0.,0.])

    def test_never_guess_new_resources(self):
        """[CHATGPT_FIX_2026-11-21] Empty memory retains selected quiet-zone hold."""
        self.assertEqual(self.goal(),[0.,0.])
        self.obs['t']=50.
        self.assertEqual(self.goal(),[0.,0.])


if __name__=='__main__':
    unittest.main()
