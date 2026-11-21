"""[CODEX_ENHANCEMENT_2026-11-21] Tactical regression fixtures, not full matches."""
import copy
import math
import unittest

from test_agent import recording
from agent.observation import Observer
from agent.strategy import Strategy
from agent.navigation import Navigator
from agent.routing import Router
from agent.energy import EnergyPolicy
from agent.combat import Combat
from agent.tuning import DEFAULT


class FlatWorld:
    """Small controlled geometry fixture; no weapons/game physics simulation."""
    def __init__(self, boxes=()):
        self.boxes = boxes

    def ground(self,x,y):
        return 0.

    def solid(self,x,y,z):
        return any(a<=x<=b and c<=y<=d and 0<z<30 for a,b,c,d in self.boxes)

    def clear(self,a,b):
        return all(not self.solid(*(a[k]+(b[k]-a[k])*i/100 for k in range(3))) for i in range(1,100))

    def walkable(self,a,b,stats):
        r = stats.get('radius',2.5)
        return all(not any(x-r<=a[0]+(b[0]-a[0])*i/40<=xx+r and y-r<=a[1]+(b[1]-a[1])*i/40<=yy+r
                           for x,xx,y,yy in self.boxes) for i in range(41))


class SurvivalTests(unittest.TestCase):
    def setUp(self):
        self.hello,observations = recording()
        self.o = copy.deepcopy(observations[0])
        self.o.update(t=10,tick=200,alive=16,mechs=[],projectiles=[],events=[],sounds=[],pickups=[],crates=[],cubes=[],drops=[],offer=None)
        self.o['self'].update(pos=[0.,0.,0.],vel=[0.,0.,0.],aim=[0.,0.],hp=1400,max_hp=1400,energy=100,max_energy=100,grounded=True,in_zone=True)
        self.o['self']['weapons'] = [dict(kind='gun',cooldown=0,ammo=12,reload=0,stats=self.hello['config']['weapons']['gun']),None]
        self.o['zone'] = dict(center=[0,0],radius=400,next_center=[0,0],next_radius=250,shrink_start=60,shrink_end=110,dps=20)
        self.world = FlatWorld()
        self.observer = Observer(self.world)

    def enemy(self,id=1,x=60,y=0,approach=True):
        d = math.hypot(x,y)
        return dict(id=id,kind='mech',pos=[x,y,0],vel=[-x/d*10,-y/d*10,0] if approach else [0,0,0],
                    aim=[math.atan2(-y,-x) if approach else math.atan2(y,x),0],hp=1000,max_hp=1400,weapons=['gun'])

    def situation(self):
        return self.observer.parse(self.o)

    def test_multiple_pursuers_and_crossfire(self):
        self.o['mechs'] = [self.enemy(1),self.enemy(2,x=-60)]
        s = self.situation()
        self.assertEqual(s.pursuing,2)
        self.assertGreater(s.crossfire,.9)
        self.assertTrue(s.emergency)
        self.assertEqual(Strategy().choose(s),'conservative')

    def test_visible_bystanders_are_not_pursuers(self):
        self.o['mechs'] = [self.enemy(1,approach=False),self.enemy(2,x=-60,approach=False)]
        passive = self.situation()
        self.assertEqual(passive.pursuing,0)
        self.o['mechs'] = [self.enemy(1),self.enemy(2,x=-60)]
        self.assertGreater(self.situation().pressure,passive.pressure+1)

    def test_low_health_emergency_and_damage_memory(self):
        self.o['self']['hp'] = 250
        self.o['mechs'] = [self.enemy()]
        self.o['events'] = [dict(type='damaged',by=1,amount=100,weapon='gun',bearing=0)]
        s = self.situation()
        self.assertTrue(s.emergency)
        self.o['events'] = []
        self.o['t'] += .5
        self.assertEqual(self.situation().recent_damage,100)
        self.o['t'] += DEFAULT.damage_window
        self.assertEqual(self.situation().recent_damage,0)

    def test_zone_travel_starts_early_and_suppresses_loot(self):
        self.o['zone'].update(next_center=[200,0],next_radius=25,shrink_end=45)
        self.o['t'] = 15
        self.o['cubes'] = [dict(id=5001,pos=[-20,0,0])]
        s = self.situation()
        self.assertTrue(s.urgent)
        goal = Strategy().goal(s,'conservative')
        self.assertGreater(goal[0],180)

    def test_no_aggression_without_energy_or_escape(self):
        e = self.enemy(x=30)
        e['hp'] = 100
        self.o['mechs'] = [e]
        self.o['self']['energy'] = 10
        self.assertNotEqual(Strategy().choose(self.situation()),'aggressive')
        self.o['self']['energy'] = 100
        s = self.situation()
        s.escape_fraction = .125
        self.assertNotEqual(Strategy().choose(s),'aggressive')
        s.escape_fraction = 1
        self.assertEqual(Strategy().choose(s),'aggressive')

    def test_obstacles_reduce_escape_routes(self):
        self.observer.world = FlatWorld(((4,20,-20,20),(-20,-4,-20,20)))
        s = self.situation()
        self.assertLess(s.escape_fraction,.5)
        self.assertGreater(len(s.escape_routes),0)

    def test_bounded_route_around_building(self):
        world = FlatWorld(((15,35,-12,12),))
        router = Router(world)
        s = self.situation()
        for i in range(100):
            before = router.expansions
            router.waypoint(s,[60,0])
            self.assertLessEqual(router.expansions-before,DEFAULT.route_expansions_per_tick)
            s.obs['t'] += .1
            if router.path:
                break
        self.assertTrue(router.path)
        self.assertTrue(any(abs(p[1])>=20 for p in router.path))
        previous = s.me['pos']
        for p in router.path:
            self.assertTrue(world.walkable(previous,p,s.me['stats']))
            previous = p

    def test_route_fallback_when_search_cannot_finish(self):
        world = FlatWorld(((-20,20,-20,20),))
        router = Router(world)
        s = self.situation()
        self.assertEqual(router.waypoint(s,[60,0]),[60,0])
        self.assertEqual(router.path,[])

    def test_projectile_changes_local_movement(self):
        s = self.situation()
        nav = Navigator(self.world)
        safe,_ = nav.local_move(s,[100,0],'balanced')
        self.o['projectiles'] = [dict(id=1,kind='gun',pos=[40,0,4.5],vel=[-100,0,0])]
        dodge,_ = Navigator(self.world).local_move(self.situation(),[100,0],'balanced')
        self.assertGreater(abs(dodge[1]),abs(safe[1])+.2)

    def test_energy_burst_recovery_and_no_airborne_jet(self):
        s = self.situation()
        s.pursuing,s.pressure = 1,2
        energy = EnergyPolicy()
        self.assertTrue(energy.boost(s,[1,0]))
        s.me['energy'] = 35
        self.assertFalse(energy.boost(s,[1,0]))
        s.me['energy'] = 55
        self.assertFalse(energy.boost(s,[1,0]))
        s.me['energy'] = 100
        self.assertTrue(energy.boost(s,[1,0]))
        s.me['energy'],s.emergency = 10,True
        self.assertTrue(energy.boost(s,[1,0]))
        s.me['grounded'] = False
        self.assertFalse(energy.boost(s,[1,0]))

    def test_distant_visible_enemy_does_not_trigger_boost(self):
        self.o['mechs'] = [self.enemy(x=190,approach=False)]
        s = self.situation()
        self.assertFalse(EnergyPolicy().boost(s,[1,0]))

    def test_weapon_choice_reloading_gun_and_emergency_laser(self):
        combat = Combat(self.hello['config'],self.world)
        s = self.situation()
        laser = dict(kind='laser',cooldown=0,charge=0,stats=self.hello['config']['weapons']['laser'])
        s.me['weapons'][0]['reload'] = 1
        s.me['weapons'][1] = laser
        self.assertIs(combat.select_weapon(s.me['weapons'],100,s,self.enemy()),laser)
        s.emergency = True
        self.assertIsNone(combat.select_weapon(s.me['weapons'],100,s,self.enemy()))
        laser['charge'] = .5
        self.assertIs(combat.select_weapon(s.me['weapons'],100,s,self.enemy()),laser)

    def test_laser_charge_release_and_lightning_energy_reserve(self):
        self.o['mechs'] = [self.enemy(x=30,approach=False)]
        s = self.situation()
        laser = dict(kind='laser',cooldown=0,charge=0,stats=self.hello['config']['weapons']['laser'])
        s.me['weapons'][1] = laser
        combat = Combat(self.hello['config'],self.world)
        aim,fire,_ = combat.act(s,'balanced')
        self.assertTrue(fire[1])
        s.me['aim'] = aim
        laser['charge'] = laser['stats']['charge']
        self.assertFalse(combat.act(s,'balanced')[1][1])
        s.me['weapons'][1] = dict(kind='lightning',cooldown=0,stats=self.hello['config']['weapons']['lightning'])
        s.me['energy'] = 20
        self.assertFalse(combat.act(s,'balanced')[1][1])
        s.me['energy'] = 100
        self.assertTrue(combat.act(s,'balanced')[1][1])

    def test_observable_phase_transitions(self):
        self.assertEqual(self.situation().phase,'early')
        self.o['t'] = 160
        self.assertEqual(self.situation().phase,'mid')
        self.o['zone']['radius'] = 70
        self.assertEqual(self.situation().phase,'late')

    def test_zone_boundary_retreat_moves_inward(self):
        self.o['self']['pos'] = [80,0,0]
        self.o['zone'].update(radius=85,next_radius=50)
        self.o['mechs'] = [self.enemy(x=120)]
        self.o['self']['in_zone'] = False
        s = self.situation()
        goal = Strategy().goal(s,'conservative')
        move,_ = Navigator(self.world).local_move(s,goal,'conservative')
        self.assertLess(move[0],0)

    def test_stuck_recovery_and_route_size_invalidation(self):
        nav = Navigator(self.world)
        s = self.situation()
        nav.local_move(s,[100,0],'balanced')
        s.obs['t'] += 2
        nav.local_move(s,[100,0],'balanced')
        self.assertGreater(nav.escape_until,s.obs['t'])
        router = Router(self.world)
        router.waypoint(s,[60,0])
        before = router.shape
        s.me['stats']['radius'] = before[0]*1.5
        router.waypoint(s,[60,0])
        self.assertNotEqual(router.shape,before)


if __name__ == '__main__':
    unittest.main()
