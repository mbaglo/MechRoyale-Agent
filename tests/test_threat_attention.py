"""[CODEX_ENHANCEMENT_2026-11-21] EXP-009 defensive-yaw persistence."""
import copy
import math
from types import SimpleNamespace
import unittest
from test_agent import recording
from agent.combat import Combat,angle_delta
from agent.observation import Observer


class ThreatAttentionTests(unittest.TestCase):
    def setUp(self):
        h,observations=recording();self.o=copy.deepcopy(observations[0])
        self.o.update(t=10,mechs=[],crates=[],events=[],sounds=[])
        self.o['self'].update(pos=[0,0,0],aim=[0,0],hp=1400,max_hp=1400)
        self.combat=Combat(h['config'],SimpleNamespace(clear=lambda a,b:True));self.observer=Observer()

    def act(self):return self.combat.act(self.observer.parse(self.o),'balanced')

    def test_single_charge_sound_is_retained_during_turn(self):
        self.o['sounds']=[dict(kind='laser_charge',bearing=math.pi,dist='near',age=0)]
        first=self.act()[0][0]
        self.o['sounds']=[];self.o['t']+=.4
        self.assertAlmostEqual(self.act()[0][0],first)
        self.assertEqual(self.act()[1],[False,False])

    def test_original_scan_resumes_after_attention_expires(self):
        self.o['sounds']=[dict(kind='gun',bearing=2.,dist='mid',age=0)]
        self.act();self.o['sounds']=[];self.o['t']+=3
        self.assertAlmostEqual(self.act()[0][0],angle_delta(self.o['t']*.6,0))

    def test_damage_and_fresh_sound_update_the_bearing(self):
        self.o['events']=[dict(type='damaged',amount=45,by=5,weapon='gun',bearing=1.)]
        self.assertAlmostEqual(self.act()[0][0],1.)
        self.o['events']=[];self.o['sounds']=[dict(kind='gun',bearing=-1.,dist='near',age=0)];self.o['t']+=.1
        self.assertAlmostEqual(self.act()[0][0],-1.)

    def test_visible_target_still_controls_aim(self):
        self.o['sounds']=[dict(kind='laser_charge',bearing=math.pi,dist='near',age=0)]
        self.act();self.o['sounds']=[]
        self.o['mechs']=[dict(id=5,kind='mech',pos=[100,0,0],vel=[0,0,0],aim=[math.pi,0],hp=1400)]
        self.assertAlmostEqual(self.act()[0][0],0.)

    def test_turn_rate_fixture_faces_rear_attacker_before_charge_finishes(self):
        # Torso-only rate integration, not a combat or survival simulator.
        self.o['sounds']=[dict(kind='laser_charge',bearing=math.pi,dist='near',age=0)]
        yaw=0.;rate=self.o['self']['stats']['turn_rate']
        for _ in range(5):
            desired=self.act()[0][0];delta=angle_delta(desired,yaw)
            yaw += max(-rate*.1,min(rate*.1,delta))
            self.o['self']['aim'][0]=yaw;self.o['sounds']=[];self.o['t']+=.1
        self.assertLess(abs(angle_delta(math.pi,yaw)),math.pi/2)


if __name__=='__main__':unittest.main()
