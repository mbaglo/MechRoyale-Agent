"""[CODEX_ENHANCEMENT_2026-11-21] EXP-012 gun-only retreat change."""
import copy,math,unittest
from types import SimpleNamespace
from test_agent import recording
from agent.observation import Observer
from agent.combat import Combat


class RetreatGunTests(unittest.TestCase):
    def setUp(self):
        h,obs=recording();self.h=h;self.o=copy.deepcopy(obs[0]);self.o.update(t=10,events=[],sounds=[],crates=[])
        self.o['self'].update(pos=[0,0,0],aim=[0,math.atan2(-2.5,100)],hp=200)
        self.o['self']['weapons']=[dict(kind='gun',cooldown=0,ammo=12,reload=0,stats=h['config']['weapons']['gun']),None]
        self.o['mechs']=[dict(id=5,kind='mech',pos=[100,0,0],vel=[0,0,0],aim=[math.pi,0],hp=1400)]
        self.world=SimpleNamespace(clear=lambda a,b:True);self.combat=Combat(h['config'],self.world)

    def act(self):return self.combat.act(Observer().parse(self.o),'conservative')

    def test_aligned_gun_can_fire_during_retreat(self):
        self.assertEqual(self.act()[1],[True,False])

    def test_absent_or_occluded_target_remains_quiet(self):
        self.world.clear=lambda a,b:False
        self.assertEqual(self.act()[1],[False,False])
        self.world.clear=lambda a,b:True;self.o['mechs']=[]
        self.assertEqual(self.act()[1],[False,False])

    def test_ammo_reload_cooldown_and_alignment_still_gate_shots(self):
        gun=self.o['self']['weapons'][0]
        for field,value in [('ammo',0),('reload',1),('cooldown',1)]:
            old=gun[field];gun[field]=value;self.assertFalse(self.act()[1][0]);gun[field]=old
        self.o['self']['aim']=[math.pi,0]
        self.assertFalse(self.act()[1][0])

    def test_range_is_enforced(self):
        self.o['mechs'][0]['pos'][0]=300
        self.o['self']['aim']=[0,math.atan2(-2.5,300)]
        self.assertFalse(self.act()[1][0])

    def test_secondary_laser_retreat_veto_is_retained(self):
        self.o['self']['weapons'][1]=dict(kind='laser',cooldown=0,charge=0,stats=self.h['config']['weapons']['laser'])
        self.assertFalse(self.act()[1][1])


if __name__=='__main__':unittest.main()
