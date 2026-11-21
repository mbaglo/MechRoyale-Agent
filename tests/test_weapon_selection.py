"""[ASTRA_FIX_2026-11-21] Verify the game gun works when the other slot is unusable."""
import copy
import math
from types import SimpleNamespace
import unittest
from test_agent import recording
from agent.combat import Combat
from agent.observation import Observer


class WeaponSelectionTests(unittest.TestCase):
    def setUp(self):
        self.hello, obs = recording()
        self.o = copy.deepcopy(obs[0])
        self.o['self'].update(pos=[0,0,0], aim=[0,0], energy=100)
        self.o['self']['weapons'][0].update(cooldown=0, reload=0, ammo=12)
        self.o['mechs'] = [dict(id=5,kind='mech',hp=1000,pos=[100,0,0],vel=[0,10,0])]
        self.c = Combat(self.hello['config'], SimpleNamespace(clear=lambda *_: True))

    def equip(self, kind):
        self.o['self']['weapons'][1] = dict(kind=kind, stats=self.hello['config']['weapons'][kind], cooldown=0)

    def act_aligned(self, mode):
        s = Observer().parse(self.o)
        aim = self.c.act(s,mode)[0]
        s.me['aim'] = aim
        return self.c.act(s,mode)[:2]

    def test_loaded_mortar_does_not_silence_retreat_gun(self):
        self.equip('mortar')
        aim, fire = self.act_aligned('conservative')
        self.assertEqual(fire,[True,False])
        self.assertGreater(aim[0],0)

    def test_close_mortar_uses_gun_and_valid_distant_mortar_keeps_priority(self):
        self.equip('mortar')
        self.o['mechs'][0]['pos'][0] = 15
        self.assertEqual(self.act_aligned('balanced')[1],[True,False])
        self.o['mechs'][0]['pos'][0] = 100
        self.assertEqual(self.act_aligned('balanced')[1],[False,True])

    def test_vetoed_laser_and_depleted_lightning_preserve_gun_lead(self):
        for kind in ('laser','lightning'):
            with self.subTest(kind=kind):
                self.equip(kind)
                self.o['mechs'][0]['pos'][0] = 100 if kind=='laser' else 30
                self.o['self']['energy'] = 1
                aim, fire = self.act_aligned('conservative')
                self.assertGreater(aim[0],0)
                self.assertEqual(fire,[True,False])
