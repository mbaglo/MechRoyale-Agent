"""[CODEX_ENHANCEMENT_2026-11-21] Recorded observations and policy regressions."""
import copy
import gzip
import importlib.util
import json
import math
from pathlib import Path
import time
import unittest

from agent.policy import Bot
from agent.combat import intercept
from agent.world import inside

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT/'official'/'mechfight-kit'


def recording():
    with gzip.open(KIT/'check'/'stream.jsonl.gz','rt') as f:
        messages = [json.loads(line) for line in f]
    hello = messages[0]
    hello['map']['dir'] = str(KIT/'arena')
    return hello, [m for m in messages if m['type']=='obs']


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hello, cls.observations = recording()
        spec = importlib.util.spec_from_file_location('official_check',KIT/'check'/'check.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.schema = module.Schema(KIT/'mechfight.schema.json')

    def setUp(self):
        self.bot = Bot(copy.deepcopy(self.hello))
        self.obs = copy.deepcopy(self.observations[0])

    def quiet(self):
        o = self.obs
        for name in ('mechs','projectiles','events','sounds','pickups','cubes','drops','crates'):
            o[name] = []
        o['t'] = 10
        o['zone'] = dict(center=o['self']['pos'][:2],next_center=o['self']['pos'][:2],radius=500,next_radius=300,shrink_start=60,shrink_end=110,dps=20)
        o['self']['hp'] = o['self']['max_hp']
        o['self']['in_zone'] = True
        return o

    def enemy(self, distance=30, hp=100):
        p = self.obs['self']['pos']
        return dict(id=5,kind='mech',pos=[p[0]+distance,p[1],p[2]],vel=[0,0,0],aim=[math.pi,0],hp=hp,max_hp=1400,weapons=['gun'])

    def test_recorded_actions_and_runtime(self):
        timings = []
        for obs in self.observations:
            start = time.perf_counter()
            action = self.bot.act(obs)
            timings.append((time.perf_counter()-start)*1000)
            self.assertEqual(self.schema.errors(action,'Action'),[])
            self.assertEqual(action['tick'],obs['tick'])
            self.assertLessEqual(math.hypot(*action['move']),1.000001)
            self.assertTrue(all(math.isfinite(v) for v in action['aim']))
        # Headroom check for decision CPU time; official checker measures transport too.
        self.assertLess(sorted(timings)[int(.99*len(timings))],40)

    def test_modes_and_health_hysteresis(self):
        o = self.quiet()
        o['mechs'] = [self.enemy()]
        self.assertEqual(self.bot.strategy.choose(self.bot.observer.parse(o)),'aggressive')
        o['self']['hp'] = o['self']['max_hp']*.2
        self.assertEqual(self.bot.strategy.choose(self.bot.observer.parse(o)),'conservative')
        o['self']['hp'] = o['self']['max_hp']*.5
        self.assertEqual(self.bot.strategy.choose(self.bot.observer.parse(o)),'conservative')

    def test_outnumbered_and_zone_urgency(self):
        o = self.quiet()
        o['mechs'] = [self.enemy(),dict(self.enemy(40),id=6)]
        self.assertEqual(self.bot.strategy.choose(self.bot.observer.parse(o)),'conservative')
        o['mechs'] = []
        o['self']['in_zone'] = False
        self.assertTrue(self.bot.observer.parse(o).urgent)

    def test_zone_deadline_depends_on_remaining_trip(self):
        # [ASTRA_FIX_2026-11-21] [CODEX_FIX_2026-11-21]
        o = self.quiet()
        o['t'] = o['zone']['shrink_end'] - 1
        o['mechs'] = [self.enemy()]
        self.bot.act(o)
        self.assertEqual(self.bot.mode, 'aggressive')
        x, y = o['self']['pos'][:2]
        o['zone']['next_center'] = [x + o['zone']['next_radius'] - 5, y]
        self.bot.act(o)
        self.assertEqual(self.bot.mode, 'conservative')
        o['zone'].update(next_center=[x, y], next_radius=0)
        self.assertTrue(self.bot.observer.parse(o).urgent)

    def test_extended_trip_requires_two_nearby_cubes_and_no_opponent(self):
        # [ASTRA_ENHANCEMENT_2026-11-21] [CODEX_ENHANCEMENT_2026-11-21]
        o = self.quiet()
        x, y, z = o['self']['pos']
        first = dict(id=5001, pos=[x + 148., y, z])
        o['cubes'] = [first]
        def goal():
            s = self.bot.observer.parse(o)
            return self.bot.strategy.goal(s, self.bot.strategy.choose(s))
        self.assertNotEqual(goal(), first['pos'][:2])
        o['cubes'].append(dict(id=5002, pos=[x + 151., y, z]))
        self.assertEqual(goal(), first['pos'][:2])
        o['mechs'] = [self.enemy(70)]
        self.assertNotEqual(goal(), first['pos'][:2])

    def test_retreat_preserves_regeneration(self):
        o = self.quiet()
        o['mechs'] = [self.enemy(100)]
        o['self']['hp'] = 100
        action = self.bot.act(o)
        self.assertEqual(action['fire'],[False,False])

    def test_intercept_leads_moving_enemy(self):
        p = intercept([0,0,0],[100,0,0],[0,10,0],100)
        self.assertGreater(p[1],10)
        self.assertAlmostEqual(math.dist([0,0,0],p)/100,p[1]/10)

    def test_pickup_vertical_range_and_upgrade(self):
        o = self.quiet()
        p = o['self']['pos']
        o['self']['weapons'][1] = None
        o['pickups'] = [dict(id=8001,kind='laser',pos=[p[0],p[1],p[2]+5])]
        self.assertNotIn('take',self.bot.act(o))
        o['pickups'][0]['pos'][2] = p[2]
        o['offer'] = dict(id=1,expires=20,choices=[dict(id='sensors'),dict(id='armor'),dict(id='gun_rate')])
        action = self.bot.act(o)
        self.assertEqual(action['take'],8001)
        self.assertEqual(action['pick'],1)

    def test_unknown_fields_and_determinism(self):
        a, b = Bot(self.hello), Bot(self.hello)
        for o in self.observations[::10]:
            altered = dict(o,future_extension={'anything':42})
            self.assertEqual(a.act(o),b.act(altered))

    def test_geometry_hole_bridge_and_terrain(self):
        self.assertTrue(inside(5,5,[0,0,10,0,10,10,0,10]))
        w = self.bot.world
        old_cells, old_prisms = w.cells,w.prisms
        p = dict(base=10,top=20,ring=[0,0,10,0,10,10,0,10],holes=[[3,3,7,3,7,7,3,7]])
        w.cells,w.prisms = {(0,0):[0]},[(p,(0,0,10,10))]
        self.assertFalse(w.solid(1,1,5))
        self.assertTrue(w.solid(1,1,15))
        self.assertFalse(w.solid(5,5,15))
        w.cells,w.prisms = old_cells,old_prisms
        self.assertTrue(math.isfinite(w.ground(0,0)))

    def test_no_targets_no_firing_and_reload(self):
        o = self.quiet()
        o['self']['weapons'][0]['ammo'] = 0
        action = self.bot.act(o)
        self.assertEqual(action['fire'],[False,False])
        self.assertTrue(action['reload'])

    def test_stationary_goal_and_missing_map(self):
        self.assertEqual(self.bot.act(self.quiet())['move'],[0.,0.])
        h = copy.deepcopy(self.hello)
        h['map']['dir'] = str(ROOT/'does-not-exist')
        with self.assertRaises(RuntimeError):
            Bot(h)


if __name__ == '__main__':
    unittest.main()
