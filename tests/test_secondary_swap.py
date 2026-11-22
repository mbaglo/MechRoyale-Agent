"""[CHATGPT_ENHANCEMENT_2026-11-21] Safe full-slot take+drop weapon regressions."""
import copy
import unittest

from test_agent import recording
from agent.observation import Observer
from agent.policy import Bot
from agent.weapon_swap import safe_laser_replacements


class SecondarySwapTests(unittest.TestCase):
    def setUp(self):
        hello, observations = recording()
        self.bot = Bot(hello)
        self.obs = copy.deepcopy(observations[0])
        me = self.obs['self']
        me.update(pos=[0., 0., 0.], hp=me['max_hp'], grounded=True, in_zone=True)
        me['weapons'] = [
            dict(kind='gun', ammo=12, reload=0., cooldown=0.,
                 stats=copy.deepcopy(hello['config']['weapons']['gun'])),
            dict(kind='lightning', cooldown=0.,
                 stats=copy.deepcopy(hello['config']['weapons']['lightning'])),
        ]
        self.obs.update(t=10., mechs=[], projectiles=[], events=[], sounds=[],
                        drops=[], crates=[], cubes=[], offer=None)
        self.obs['zone'] = dict(center=[0., 0.], radius=550.,
                                next_center=[0., 0.], next_radius=350.,
                                shrink_start=70., shrink_end=140., dps=20.)
        self.obs['pickups'] = [dict(id=8101, kind='laser', pos=[2., 0., 0.])]

    def action(self):
        return self.bot.act(copy.deepcopy(self.obs))

    def eligible(self):
        return safe_laser_replacements(Observer().parse(copy.deepcopy(self.obs)))

    def test_atomic_take_and_drop_secondary_only(self):
        a = self.action()
        self.assertEqual((a.get('take'), a.get('drop')), (8101, 1))
        self.assertEqual(a['tick'], self.obs['tick'])

    def test_seek_visible_replacement_without_empty_slot(self):
        self.obs['pickups'][0]['pos'] = [35., 0., 0.]
        situation = Observer().parse(self.obs)
        goal = self.bot.strategy.goal(situation, 'balanced')
        self.assertEqual(goal, [35., 0.])
        self.assertNotIn('take', self.action())

    def test_existing_empty_slot_pickup_is_preserved(self):
        self.obs['self']['weapons'][1] = None
        a = self.action()
        self.assertEqual(a.get('take'), 8101)
        self.assertNotIn('drop', a)

    def test_no_swap_from_gun_laser_or_unwanted_mortar(self):
        self.obs['self']['weapons'][1]['kind'] = 'laser'
        self.obs['pickups'][0]['kind'] = 'mortar'
        self.assertNotIn('take', self.action())
        self.obs['self']['weapons'][1]['kind'] = 'lightning'
        self.assertNotIn('take', self.action())

    def test_enemy_or_low_health_disables_swap_and_detour(self):
        self.obs['mechs'] = [dict(id=5, kind='mech', pos=[50., 0., 0.],
                                  vel=[0., 0., 0.], aim=[0., 0.], hp=1400)]
        self.assertEqual(self.eligible(), [])
        self.assertNotIn('take', self.action())
        self.obs['mechs'] = []
        self.obs['self']['hp'] = self.obs['self']['max_hp'] * .8
        self.assertEqual(self.eligible(), [])
        self.assertNotIn('take', self.action())

    def test_zone_grounding_and_capture_protected(self):
        self.obs['self']['in_zone'] = False
        self.assertNotIn('take', self.action())
        self.obs['self']['in_zone'] = True
        self.obs['self']['grounded'] = False
        self.assertNotIn('take', self.action())
        self.obs['self']['grounded'] = True
        self.obs['drops'] = [dict(holder=self.obs['self']['id'], progress=1.)]
        self.assertNotIn('take', self.action())

    def test_damage_warning_sound_and_projectile_protected(self):
        self.obs['events'] = [dict(type='damaged', amount=45., bearing=0.)]
        self.assertNotIn('take', self.action())
        self.obs['events'] = []
        self.obs['sounds'] = [dict(kind='laser_charge', dist='mid', bearing=1.)]
        self.assertNotIn('take', self.action())
        self.obs['sounds'] = []
        self.obs['projectiles'] = [dict(kind='gun', pos=[25., 0., 4.],
                                        vel=[-100., 0., 0.])]
        self.assertNotIn('take', self.action())

    def test_take_range_height_and_visible_kind(self):
        self.obs['pickups'][0]['pos'] = [5., 0., 0.]
        self.assertNotIn('take', self.action())
        self.obs['pickups'][0]['pos'] = [2., 0., 4.1]
        self.assertNotIn('take', self.action())
        self.obs['pickups'][0]['kind'] = 'mortar'
        self.obs['pickups'][0]['pos'] = [2., 0., 0.]
        self.assertNotIn('take', self.action())


if __name__ == '__main__':
    unittest.main()
