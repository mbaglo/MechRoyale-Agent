"""[CODEX_ENHANCEMENT_2026-11-21] EXP-011 upgrade-choice regressions."""
import copy
import unittest
from test_agent import recording
from agent.policy import Bot


class MagazinePriorityTests(unittest.TestCase):
    def setUp(self):
        h,observations=recording();self.h=h;self.o=copy.deepcopy(observations[0]);self.bot=Bot(h)
        self.o['offer']=dict(id=1,expires=20,choices=[])

    def pick(self,ids):
        self.o['offer']['choices']=[dict(id=id) for id in ids]
        return self.bot.act(self.o)['pick']

    def test_magazine_precedes_repairs_when_offered(self):
        self.assertEqual(self.pick(['nanites','armor','gun_mag']),2)

    def test_choice_index_follows_offer_order(self):
        self.assertEqual(self.pick(['gun_mag','nanites','armor']),0)

    def test_original_non_magazine_ranking_is_retained(self):
        self.assertEqual(self.pick(['gun_damage','armor','nanites']),2)
        self.assertEqual(self.pick(['sensors','armor','gun_rate']),1)

    def test_no_offer_produces_no_choice(self):
        self.o['offer']=None
        self.assertNotIn('pick',self.bot.act(self.o))

    def test_official_fixture_documents_the_expected_effects(self):
        upgrade=next(u for u in self.h['config']['upgrades'] if u['id']=='gun_mag')
        self.assertTrue(any(e['path']=='weapons.gun.mag' and e.get('add',0)>0 for e in upgrade['effects']))
        self.assertTrue(any(e['path']=='weapons.gun.reload' and e.get('mul',1)<1 for e in upgrade['effects']))


if __name__=='__main__':unittest.main()
