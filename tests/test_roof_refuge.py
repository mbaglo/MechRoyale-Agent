"""[CODEX_ENHANCEMENT_2026-11-21] Geometry/intent fixtures, not flight simulation."""
import copy
import math
from pathlib import Path
import unittest
from test_agent import recording,KIT
from agent.world import World
from agent.roof import RoofRefuge
from agent.observation import Observer


def rectangular_world(base=0,top=20):
    w=object.__new__(World)
    p=dict(kind='building',base=base,top=top,ring=[10,-25,50,-25,50,25,10,25],holes=[])
    w.prisms=[(p,(10,-25,50,25))]
    w.cells={(x,y):[0] for x in (0,1) for y in (-1,0)}
    w.bounds=dict(minX=-200,maxX=200,minY=-200,maxY=200)
    w.ground=lambda x,y:0.
    return w


class RoofRefugeTests(unittest.TestCase):
    def setUp(self):
        _,observations=recording();self.o=copy.deepcopy(observations[0])
        self.o.update(t=10,events=[],projectiles=[],crates=[],pickups=[],drops=[],sounds=[],cubes=[])
        self.o['self'].update(pos=[0,0,0],vel=[0,0,0],hp=500,max_hp=1400,energy=100,max_energy=100,grounded=True,in_zone=True)
        self.o['mechs']=[dict(id=5,kind='mech',pos=[-30,0,0],vel=[0,0,0],aim=[0,0],hp=1400)]
        self.o['zone']=dict(center=[0,0],radius=500,next_center=[0,0],next_radius=300,shrink_start=100,shrink_end=200,dps=20)
        self.world=rectangular_world();self.roof=RoofRefuge(self.world)

    def situation(self):return Observer().parse(self.o)

    def action(self):return dict(move=[1,0],boost=True,jump=False,fire=[True,False])

    def test_map_checked_site_and_launch_are_feasible(self):
        target=self.roof.choose(self.situation())
        self.assertIsNotNone(target)
        self.assertTrue(self.world.walkable(self.o['self']['pos'],target['launch'],self.o['self']['stats']))
        self.assertTrue(self.roof.vertical_clear(target['launch'],target['point'][2]+1,self.o['self']['stats']))
        self.assertTrue(self.roof.supported(*target['point'][:2],target['prism'],5.5))

    def test_approach_reserves_energy_and_stops_outgoing_damage(self):
        self.roof.goal(self.situation(),[0,0])
        self.assertIsNotNone(self.roof.target)
        a=self.roof.apply(self.situation(),self.action())
        self.assertFalse(a['boost']);self.assertFalse(a['jump']);self.assertEqual(a['fire'],[False,False])

    def test_jump_climb_traverse_and_landing_intentions(self):
        self.roof.goal(self.situation(),[0,0]);target=self.roof.target
        self.o['self']['pos']=target['launch'][:]
        self.roof.goal(self.situation(),[0,0])
        a=self.roof.apply(self.situation(),self.action())
        self.assertTrue(a['jump']);self.assertTrue(a['boost']);self.assertEqual(a['move'],[0.,0.])
        self.o['self'].update(grounded=False,pos=[*target['launch'][:2],target['point'][2]+1])
        a=self.roof.apply(self.situation(),self.action())
        self.assertGreater(math.hypot(*a['move']),.4)
        self.o['self']['pos']=[target['point'][0],target['point'][1],target['point'][2]+1]
        self.assertFalse(self.roof.apply(self.situation(),self.action())['boost'])
        self.o['self'].update(grounded=True,pos=target['point'][:])
        self.roof.goal(self.situation(),[0,0])
        self.assertEqual(self.roof.phase,'hold')
        self.assertEqual(self.roof.apply(self.situation(),self.action())['move'],[0.,0.])

    def test_low_energy_or_no_threat_preserves_original_goal(self):
        self.o['self']['energy']=40
        self.assertEqual(self.roof.goal(self.situation(),[-10,0]),[-10,0]);self.assertIsNone(self.roof.target)
        self.o['self']['energy']=100;self.o['mechs']=[]
        self.assertEqual(self.roof.goal(self.situation(),[-10,0]),[-10,0])

    def test_low_ceiling_and_unreachable_towers_are_rejected(self):
        self.world=rectangular_world(top=70);self.roof=RoofRefuge(self.world)
        self.assertIsNone(self.roof.choose(self.situation()))
        self.world=rectangular_world();p=dict(kind='bridge',base=12,top=14,ring=[-10,-10,10,-10,10,10,-10,10],holes=[])
        self.world.prisms.append((p,(-10,-10,10,10)))
        for x in (-1,0):
            for y in (-1,0):self.world.cells.setdefault((x,y),[]).append(1)
        self.roof=RoofRefuge(self.world)
        self.assertFalse(self.roof.vertical_clear([0,0,0],21,self.o['self']['stats']))

    def test_zone_and_enemy_on_roof_cancel_refuge(self):
        self.roof.goal(self.situation(),[0,0]);target=self.roof.target
        self.o['self']['in_zone']=False
        self.assertEqual(self.roof.goal(self.situation(),[-10,0]),[-10,0]);self.assertIsNone(self.roof.target)
        self.o['self']['in_zone']=True;self.o['t']+=6
        self.roof.goal(self.situation(),[0,0]);target=self.roof.target
        self.o['mechs'][0]['pos']=target['point'][:]
        self.assertEqual(self.roof.goal(self.situation(),[-10,0]),[-10,0]);self.assertIsNone(self.roof.target)

    def test_fifteen_observed_pursuers_remain_valid_bounded_inputs(self):
        self.o['mechs']=[dict(id=i,kind='mech',pos=[-30-i*3,i-7,0],vel=[5,0,0],aim=[0,0],hp=1400) for i in range(15)]
        goal=self.roof.goal(self.situation(),[0,0]);a=self.roof.apply(self.situation(),self.action())
        self.assertEqual(len(goal),2);self.assertLessEqual(math.hypot(*a['move']),1)

    def test_actual_arena_cached_sites_have_support(self):
        world=World(KIT/'arena');roof=RoofRefuge(world)
        self.assertGreater(len(roof.sites),0)
        self.assertLessEqual(len(roof.sites),len(world.prisms)*9)
        for x,y,top,p in roof.sites:
            self.assertTrue(roof.supported(x,y,p,5.5))
            self.assertGreaterEqual(top-world.ground(x,y),10)

    def test_actual_arena_has_clear_energy_feasible_launches(self):
        world=World(KIT/'arena');roof=RoofRefuge(world);found=None
        for p,box in world.prisms[:100]:
            if p['kind']!='building':continue
            x,y=box[0]-7,(box[1]+box[3])/2
            self.o['self']['pos']=[x,y,world.ground(x,y)]
            self.o['zone'].update(center=[x,y],next_center=[x,y])
            self.o['mechs'][0]['pos']=[x-30,y,world.ground(x-30,y)]
            found=roof.choose(self.situation())
            if found:break
        self.assertIsNotNone(found)
        self.assertTrue(roof.vertical_clear(found['launch'],found['point'][2]+1,self.o['self']['stats']))

    def test_hold_does_not_reset_regeneration_with_outgoing_fire(self):
        self.roof.goal(self.situation(),[0,0]);target=self.roof.target
        self.o['self'].update(pos=target['point'][:],grounded=True)
        self.roof.phase='hold'
        for _ in range(80):
            self.o['t']+=.1
            self.roof.goal(self.situation(),[0,0])
            self.assertEqual(self.roof.apply(self.situation(),self.action())['fire'],[False,False])

    def test_failed_approach_times_out_and_returns_original_goal(self):
        self.roof.goal(self.situation(),[0,0]);self.o['t']+=19
        self.assertEqual(self.roof.goal(self.situation(),[-10,0]),[-10,0])
        self.assertIsNone(self.roof.target)


if __name__=='__main__':unittest.main()
