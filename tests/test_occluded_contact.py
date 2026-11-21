"""[ASTRA_ENHANCEMENT_2026-11-21] Confirm torso decisions while a tracked contact is obscured."""
import math
import unittest
from types import SimpleNamespace

from test_agent import recording
from agent.combat import Combat
from agent.observation import Observer


class OccludedContactTests(unittest.TestCase):
    def setUp(self):
        h,frames = recording()
        self.o = frames[0]
        self.o.update(t=4,events=[],sounds=[],crates=[],mechs=[])
        self.me = self.o['self']
        self.me.update(pos=[0,0,0],aim=[0,0])
        self.observer = Observer()
        self.combat = Combat(h['config'],SimpleNamespace(clear=lambda a,b: False))
        self.enemy = dict(id=3,kind='mech',pos=[0,95,12],vel=[0,0,0],hp=1400,cubes=2)
        self.o['mechs'].append(self.enemy)

    def act(self):
        s = self.observer.parse(self.o)
        return self.combat.act(s,'balanced')

    def test_track_through_cover_and_release_on_lost_contact(self):
        aim,fire,_ = self.act()
        self.assertAlmostEqual(aim[0],math.pi/2)
        self.assertGreater(aim[1],0)
        self.assertEqual(fire,[False,False])
        self.o['mechs'] = []
        self.assertAlmostEqual(self.act()[0][0],self.o['t']*.6)

    def test_separate_attack_bearing_overrides_hidden_contact(self):
        self.o['events'] = [dict(type='damaged',amount=45,bearing=-1.5,by=5)]
        self.assertAlmostEqual(self.act()[0][0],-1.5)
        self.o['events'] = []
        self.o['t'] += .2
        self.assertAlmostEqual(self.act()[0][0],-1.5)

    def test_multiple_or_distant_tracks_keep_scan(self):
        self.enemy['pos'][1] = 320
        self.assertAlmostEqual(self.act()[0][0],self.o['t']*.6)
        self.enemy['pos'][1] = 95
        self.o['mechs'].append(dict(self.enemy,id=4))
        self.assertAlmostEqual(self.act()[0][0],self.o['t']*.6)

    def test_distant_anonymous_shot_and_near_warning(self):
        self.o['sounds'] = [dict(kind='gun',dist='far',bearing=-1.5)]
        self.assertAlmostEqual(self.act()[0][0],math.pi/2)
        self.o['sounds'][0]['dist'] = 'near'
        self.assertAlmostEqual(self.act()[0][0],-1.5)
