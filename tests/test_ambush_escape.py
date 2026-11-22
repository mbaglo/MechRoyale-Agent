"""[CHATGPT_FIX_2026-11-21] Unseen-fire survival regression suite.

These cases test controller behavior and bounded geometry, not placements.
"""
import copy
import math
from types import SimpleNamespace
import unittest

from agent.ambush_escape import AmbushEscape
from agent.policy import Bot
from test_agent import recording


class FlatWorld:
    def ground(self, x, y):
        return 0.

    def walkable(self, start, end, stats):
        return True

    def clear(self, start, end):
        return True


class SideCoverWorld(FlatWorld):
    def clear(self, start, end):
        # A lateral escape beyond y=5 has cover from the presumed attacker.
        return abs(end[1]) <= 5.


def scenario():
    me = dict(pos=[0.,0.,0.], stats=dict(walk_speed=12., eye_height=8.),
              in_zone=True, grounded=True)
    zone = dict(center=[0.,0.],radius=120.,next_center=[0.,0.],
                next_radius=90.)
    obs = dict(t=11., events=[], zone=zone)
    return SimpleNamespace(me=me, obs=obs, enemies=[], urgent=False)


class AmbushEscapeTests(unittest.TestCase):

    def test_direct_hit_causes_short_evasive_goal(self):
        """[CHATGPT_FIX_2026-11-21] An unseen attacker must not leave us idle."""
        s = scenario()
        s.obs['events'] = [dict(type='damaged',weapon='gun',bearing=0.,amount=45)]
        e = AmbushEscape(FlatWorld())
        g = e.goal(s)
        self.assertIsNotNone(g)
        self.assertLess(g[0],-8.)
        self.assertLessEqual(math.hypot(*g),24.01)

    def test_covered_lateral_escape_beats_exposed_straight_flight(self):
        """[CHATGPT_ENHANCEMENT_2026-11-21] Cover is useful but not invented."""
        s = scenario()
        s.obs['events'] = [dict(type='damaged',weapon='gun',bearing=0.,amount=45)]
        g = AmbushEscape(SideCoverWorld()).goal(s)
        self.assertIsNotNone(g)
        self.assertGreater(abs(g[1]),5.)

    def test_sounds_alone_never_trigger_disruptive_evasion(self):
        """[CHATGPT_FIX_2026-11-21] A noisy map is not a confirmed ambush."""
        s = scenario()
        s.obs['sounds']=[dict(kind='gun',bearing=0.,dist='near')]
        self.assertIsNone(AmbushEscape(FlatWorld()).goal(s))

    def test_missing_bearing_and_zone_damage_are_ignored(self):
        """[CHATGPT_FIX_2026-11-21] No inferred fire bearings."""
        s = scenario()
        s.obs['events']=[dict(type='damaged',weapon='gun',amount=45)]
        e=AmbushEscape(FlatWorld())
        self.assertIsNone(e.goal(s))
        s.obs['events']=[dict(type='damaged',weapon='zone',bearing=0.,amount=20)]
        self.assertIsNone(e.goal(s))

    def test_expiry_after_22_tenths_and_rearmed_by_new_hit(self):
        """[CHATGPT_FIX_2026-11-21] Escape does not persist indefinitely."""
        s=scenario()
        s.obs['events']=[dict(type='damaged',weapon='gun',bearing=0.,amount=45)]
        e=AmbushEscape(FlatWorld())
        self.assertIsNotNone(e.goal(s))
        s.obs['events']=[]
        s.obs['t']=13.
        self.assertIsNotNone(e.goal(s))
        s.obs['t']=13.3
        self.assertIsNone(e.goal(s))
        s.obs['events']=[dict(type='damaged',weapon='gun',bearing=1.,amount=45)]
        self.assertIsNotNone(e.goal(s))

    def test_visible_threat_or_urgent_zone_take_precedence(self):
        """[CHATGPT_FIX_2026-11-21] Preserve combat and zone controllers."""
        s=scenario()
        s.obs['events']=[dict(type='damaged',weapon='gun',bearing=0.,amount=45)]
        e=AmbushEscape(FlatWorld())
        s.enemies=[dict(kind='mech',id=1)]
        self.assertIsNone(e.goal(s))
        s.enemies=[]
        s.urgent=True
        self.assertIsNone(e.goal(s))
        s.urgent=False
        s.me['in_zone']=False
        self.assertIsNone(e.goal(s))

    def test_no_escape_outside_safe_zone(self):
        """[CHATGPT_FIX_2026-11-21] Avoid creating new zone damage."""
        s=scenario()
        s.me['pos']=[18.,0.,0.]
        s.obs['zone'].update(radius=25.,next_radius=24.)
        s.obs['events']=[dict(type='damaged',weapon='gun',bearing=math.pi,amount=45)]
        g=AmbushEscape(FlatWorld()).goal(s)
        if g is not None:
            self.assertLessEqual(math.hypot(*g),17.)

    def test_policy_only_uses_escape_for_otherwise_idle_goal(self):
        """[CHATGPT_FIX_2026-11-21] Do not override a resource or zone goal."""
        hello,observations=recording()
        bot=Bot(hello)
        o=copy.deepcopy(observations[0])
        o.update(t=10.,mechs=[],projectiles=[],drops=[],crates=[],
                 pickups=[],cubes=[],events=[])
        o['self']['hp']=o['self']['max_hp']
        o['self']['in_zone']=True
        p=o['self']['pos']
        o['zone'] = dict(center=p[:2],next_center=p[:2],radius=200.,
                         next_radius=120.,shrink_start=60.,shrink_end=120.,dps=20.)
        routed=[]
        bot.zone_route.waypoint=lambda s,g:g
        bot.navigator.move=lambda s,g,m,zone_detour=False: (routed.append(g) or [0.,0.],False)
        bot.ambush_escape.goal=lambda s:[p[0]-24.,p[1]]
        bot.strategy.goal=lambda s,m:p[:2]
        bot.act(o)
        self.assertEqual(routed[-1],[p[0]-24.,p[1]])
        bot.strategy.goal=lambda s,m:[p[0]+60.,p[1]]
        bot.act(o)
        self.assertEqual(routed[-1],[p[0]+60.,p[1]])


if __name__=='__main__':
    unittest.main()
