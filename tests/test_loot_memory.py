"""[ASTRA_ENHANCEMENT_2026-11-21] Follow a sighting through a turn and abandon stale destinations."""
import copy
import unittest
from test_agent import recording
from agent.policy import Bot


class LootMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hello, stream = recording()
        cls.initial = stream[0]

    def setUp(self):
        self.bot = Bot(self.hello)
        self.obs = copy.deepcopy(self.initial)
        self.obs.update(t=10, cubes=[], pickups=[], mechs=[], drops=[], sounds=[], events=[], crates=[], projectiles=[])
        self.me = self.obs['self']
        self.me.update(pos=[0, 0, 0], in_zone=True)
        self.me['weapons'][1] = None
        self.obs['zone'].update(center=[0,0], next_center=[0,0], radius=400, next_radius=300, shrink_end=110)
        self.item = dict(id=8001, pos=[0, 80, 0], kind='laser')

    def goal(self):
        s = self.bot.observer.parse(self.obs)
        return self.bot.strategy.goal(s, self.bot.strategy.choose(s))

    def test_weapon_destination_survives_loss_of_view(self):
        self.obs['pickups'] = [self.item]
        self.assertEqual(self.goal(), [0, 80])
        self.obs['pickups'] = []
        self.obs['t'] += 6.5
        self.assertEqual(self.goal(), [0, 80])
        self.obs['t'] += 12
        self.assertEqual(self.goal(), [0, 0])

    def test_abandon_empty_destination_and_never_take_an_unseen_item(self):
        self.obs['pickups'] = [self.item]
        self.bot.act(self.obs)
        self.obs['pickups'] = []
        self.me['pos'] = [0,79,0]
        self.assertNotIn('take', self.bot.act(self.obs))
        self.me['pos'] = [0,0,0]
        self.assertEqual(self.goal(), [0, 0])

    def test_reevaluate_zone_and_contestation_of_remembered_cubes(self):
        self.obs['cubes'] = [dict(id=5010,pos=[80,0,0])]
        self.assertEqual(self.goal(), [80,0])
        self.obs['cubes'] = []
        self.obs['mechs'] = [dict(kind='mech',id=5,pos=[81,0,0],hp=1400)]
        self.assertEqual(self.goal(), [0,0])
        self.obs['mechs'] = []
        self.obs['zone']['next_radius'] = 50
        self.assertEqual(self.goal(), [0,0])
