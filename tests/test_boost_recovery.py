"""[CODEX_ENHANCEMENT_2026-11-21] Energy accounting fixtures, not match simulation."""
from types import SimpleNamespace
import unittest
from agent.navigation import Navigator


class BoostRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.nav=Navigator(None)
        self.s=SimpleNamespace(me=dict(energy=100,max_energy=100,grounded=True),urgent=False)

    def test_hysteresis_recharges_before_next_burst(self):
        self.assertTrue(self.nav.manage_boost(self.s,True))
        for energy in (30,32,55,84):
            self.s.me['energy']=energy
            self.assertFalse(self.nav.manage_boost(self.s,energy>30))
        self.s.me['energy']=85
        self.assertTrue(self.nav.manage_boost(self.s,True))

    def test_urgent_and_airborne_keep_baseline_request(self):
        self.s.me['energy']=30;self.nav.manage_boost(self.s,False)
        self.s.me['energy']=50;self.s.urgent=True
        self.assertTrue(self.nav.manage_boost(self.s,True))
        self.s.urgent=False;self.s.me['grounded']=False
        self.assertTrue(self.nav.manage_boost(self.s,True))

    def test_no_requested_boost_is_added(self):
        self.assertFalse(self.nav.manage_boost(self.s,False))

    def test_capacity_upgrades_scale_recovery_target(self):
        self.s.me.update(energy=30,max_energy=130)
        self.assertFalse(self.nav.manage_boost(self.s,False))
        self.s.me['energy']=100
        self.assertFalse(self.nav.manage_boost(self.s,True))
        self.s.me['energy']=111
        self.assertTrue(self.nav.manage_boost(self.s,True))

    def test_official_default_energy_accounting_has_longer_bursts(self):
        # Only energy equations are modeled: no movement, enemies or outcomes.
        def account(use_latch):
            nav=Navigator(None);s=SimpleNamespace(me=dict(energy=100,max_energy=100,grounded=True),urgent=False)
            spent_at=-100;boost_ticks=0;resets=0;last=False
            for decision in range(450):
                requested=s.me['energy']>30
                boost=nav.manage_boost(s,requested) if use_latch else requested
                resets += bool(boost and not last);last=boost
                for half in range(2):
                    t=(decision*2+half)*.05
                    if boost:
                        s.me['energy']=max(0,s.me['energy']-17*.05);spent_at=t;boost_ticks+=1
                    elif t-spent_at>=.6:
                        s.me['energy']=min(100,s.me['energy']+18*.05)
            return boost_ticks*.05,resets
        old_seconds,old_starts=account(False)
        new_seconds,new_starts=account(True)
        self.assertGreater(new_seconds,old_seconds+5)
        self.assertLess(new_starts,old_starts)
