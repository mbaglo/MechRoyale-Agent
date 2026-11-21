"""[ASTRA_ENHANCEMENT_2026-11-21] Verify game armor coverage and the gun's return deadline."""
import math
import unittest
from types import SimpleNamespace

from agent.combat import Combat
from agent.observation import Observer
from agent.reload_guard import guard_yaw, offset
from test_agent import recording


class ReloadGuardTests(unittest.TestCase):
    def setUp(self):
        hello,frames = recording()
        self.config = hello['config']
        self.o = frames[0]
        self.me = self.o['self']
        self.me.update(pos=[0,0,0],aim=[0,0])
        self.me['weapons'][0].update(ammo=0,reload=2.4)
        self.o.update(t=10,events=[],sounds=[],crates=[],mechs=[])
        self.world = SimpleNamespace(clear=lambda *_:True)

    def group(self, angles):
        enemies = []
        for i,angle in enumerate(angles):
            bearing=math.radians(angle)
            radius=75+i*2
            enemies.append(dict(id=i+4,kind='mech',pos=[radius*math.cos(bearing),radius*math.sin(bearing),0],
                                aim=[bearing+math.pi,0],vel=[0,0,0],hp=900,cubes=0,weapons=['gun']))
        self.o['mechs'] = enemies
        return Observer().parse(self.o)

    def test_reload_covers_second_shooter_then_recovers_aim(self):
        s = self.group([0,120])
        combat=Combat(self.config,self.world)
        aim,fire,_ = combat.act(s,'balanced')
        self.assertLess(abs(offset(math.radians(120),aim[0])),math.pi/2)
        self.assertLess(abs(aim[0]),math.pi/2)
        self.assertEqual(fire,[False,False])
        self.me['weapons'][0]['reload'] = .15
        self.me['aim'][0] = aim[0]
        self.assertAlmostEqual(combat.act(s,'balanced')[0][0],0)

    def test_blocked_or_disengaged_shooter_does_not_change_aim(self):
        s = self.group([0,120])
        self.world.clear = lambda a,b: a[1] < 10
        self.assertEqual(guard_yaw(s,0,self.config,self.world),0)
        self.world.clear = lambda *_:True
        s.enemies[1]['aim'][0] = math.radians(120)
        self.assertEqual(guard_yaw(s,0,self.config,self.world),0)

    def test_active_weapon_and_single_contact_keep_firing_bearing(self):
        self.assertEqual(guard_yaw(self.group([60]),0,self.config,self.world),0)
        s=self.group([0,-130])
        self.me['weapons'][1]=dict(kind='laser')
        self.assertEqual(guard_yaw(s,0,self.config,self.world),0)
        self.me['weapons'][1]=None
        self.me['weapons'][0]['reload']=0
        self.assertEqual(guard_yaw(s,0,self.config,self.world),0)

    def test_wrapped_angles_and_small_group_spread(self):
        s=self.group([170,-65])
        yaw=math.radians(170)
        self.me['aim'][0]=yaw
        guard=guard_yaw(s,yaw,self.config,self.world)
        self.assertLess(abs(offset(guard,math.radians(-65))),math.pi/2)
        self.assertLess(abs(offset(guard,yaw)),math.pi/2)

    def simulated_reload(self, guard):
        rear_ticks=0
        last_errors=[]
        for angle in (-160,-135,-110,-95,95,110,135,160):
            s=self.group([0,angle])
            yaw=0.
            for tick in range(25):
                self.me['weapons'][0]['reload']=max(0,2.4-.1*tick)
                self.me['aim'][0]=yaw
                command=guard_yaw(s,0,self.config,self.world) if guard else 0
                limit=self.me['stats']['turn_rate']*.1
                yaw+=max(-limit,min(limit,offset(command,yaw)))
                rear_ticks+=sum(abs(offset(math.radians(a),yaw))>math.pi/2 for a in (0,angle))
            last_errors.append(abs(yaw))
        return rear_ticks,max(last_errors)

    def test_rate_limited_guard_reduces_rear_exposure_and_returns_in_time(self):
        baseline,_=self.simulated_reload(False)
        guarded,error=self.simulated_reload(True)
        self.assertLess(guarded,baseline)
        self.assertAlmostEqual(error,0)
