"""[CODEX_ENHANCEMENT_2026-11-21] Fail-closed evaluation receipt parsing."""
import unittest
from scripts.queued_evaluation import quota, scored


class EvaluationGuardTests(unittest.TestCase):
    def test_quota_requires_explicit_live_counter(self):
        self.assertEqual(quota('0 of 4 left this hour'),0)
        self.assertEqual(quota('2 OF 4 LEFT THIS HOUR'),2)
        with self.assertRaises(ValueError): quota('All systems operational')

    def test_pending_receipt_is_not_a_score(self):
        self.assertIsNone(scored('BB-12345678\nScoring\nFetching'))

    def test_terminal_score_is_parsed_from_its_status(self):
        self.assertEqual(scored('BB-12345678\nScored\n2.25\nSat 12:01 PM'),2.25)

    def test_invalid_score_is_rejected(self):
        with self.assertRaises(ValueError): scored('Scored\n16')
        with self.assertRaises(ValueError): scored('Scored')
