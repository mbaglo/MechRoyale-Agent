"""[ASTRA_ENHANCEMENT_2026-11-21] Opening equipment trips through the normal action entry."""
import unittest
from test_agent import recording
from agent.policy import Bot


class EquipmentTests(unittest.TestCase):
    def setUp(self):
        h, observations = recording()
        self.bot = Bot(h)
        self.bot.world.ground = lambda x,y: x*.08
        self.bot.world.clear = lambda *_: True
        self.bot.world.walkable = lambda *_: True
        self.o = observations[0]
        self.o.update(t=4,events=[],mechs=[],projectiles=[],sounds=[],crates=[],drops=[],pickups=[],cubes=[])
        self.o['self'].update(pos=[0,0,0],grounded=True,hp=1400,max_hp=1400,in_zone=True)
        self.o['self']['weapons'][1] = None
        self.o['zone'].update(center=[0,0],next_center=[-130,0],radius=400,next_radius=75,
                              shrink_start=110,shrink_end=150)

    def test_arms_across_ground_slope_and_abandons_route_under_pressure(self):
        self.o['pickups'] = [dict(kind='laser',id=8005,pos=[82,0,6.56])]
        self.assertGreater(self.bot.act(self.o)['move'][0],.9)
        self.o.update(t=6,pickups=[])
        self.o['self']['pos'] = [12,0,.96]
        self.assertGreater(self.bot.act(self.o)['move'][0],.9)
        self.o['events'] = [dict(type='damaged',amount=45,weapon='gun',bearing=0,by=5)]
        self.assertLess(self.bot.act(self.o)['move'][0],0)
        self.assertIsNone(self.bot.equipment.target)

    def test_visible_crate_at_range_is_opened_before_arrival(self):
        self.o['crates'] = [dict(id=1001,pos=[85,0,6.8],hp=300)]
        first = self.bot.act(self.o)
        self.assertEqual(self.bot.combat.target_id,1001)
        self.o['self']['aim'] = first['aim']
        self.o['self']['weapons'][0].update(ammo=12,reload=0,cooldown=0)
        self.assertTrue(self.bot.act(self.o)['fire'][0])
        self.o['crates'] = []
        self.assertFalse(self.bot.act(self.o)['fire'][0])

    def test_roof_and_late_return_are_excluded(self):
        self.o['pickups'] = [dict(kind='laser',id=8005,pos=[82,0,26.56])]
        self.assertLess(self.bot.act(self.o)['move'][0],0)
        self.o['pickups'][0]['pos'][2] = 6.56
        self.o['t'] = 100
        self.assertLess(self.bot.act(self.o)['move'][0],0)
