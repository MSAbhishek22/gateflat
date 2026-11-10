"""Tests for the USDG demo credit ledger (credits.py).

The ledger is demo-only (no real USDG moves) — these tests pin the
money behaviour: Decimal exactness, no negative balances, faucet
labelling, and per-account isolation.
"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from credits import CreditError, CreditLedger


class TestLedger(unittest.TestCase):
    def test_new_account_starts_at_demo_balance(self):
        led = CreditLedger()
        self.assertEqual(led.balance("alice"), Decimal("10.00"))

    def test_charge_deducts_one_run(self):
        led = CreditLedger()
        ok, bal, _ = led.charge("alice")
        self.assertTrue(ok)
        self.assertEqual(bal, Decimal("9.99"))

    def test_charge_never_goes_negative(self):
        led = CreditLedger(start_balance=Decimal("0.00"))
        ok, bal, reason = led.charge("alice")
        self.assertFalse(ok)
        self.assertEqual(bal, Decimal("0.00"))
        self.assertIn("insufficient", reason)

    def test_exact_run_count(self):
        led = CreditLedger(start_balance=Decimal("0.03"))
        for _ in range(3):
            self.assertTrue(led.charge("alice")[0])
        self.assertFalse(led.charge("alice")[0])

    def test_accounts_are_isolated(self):
        led = CreditLedger()
        led.charge("alice")
        self.assertEqual(led.balance("bob"), Decimal("10.00"))
        self.assertEqual(led.balance("alice"), Decimal("9.99"))

    def test_top_up_adds_demo_credit(self):
        led = CreditLedger(start_balance=Decimal("0.00"))
        bal, note = led.top_up("alice")
        self.assertEqual(bal, Decimal("10.00"))
        self.assertIn("demo", note.lower())
        self.assertIn("no real USDG", note)

    def test_top_up_must_be_positive(self):
        led = CreditLedger()
        with self.assertRaises(CreditError):
            led.top_up("alice", Decimal("0"))

    def test_snapshot_shape(self):
        led = CreditLedger()
        snap = led.snapshot("alice")
        self.assertEqual(snap["balance_usdg"], "10.00")
        self.assertEqual(snap["run_cost_usdg"], "0.01")
        self.assertEqual(snap["runs_remaining"], 1000)
        self.assertEqual(snap["currency"], "USDG")
        self.assertTrue(snap["demo"])

    def test_default_account(self):
        led = CreditLedger()
        self.assertEqual(led.balance(None), Decimal("10.00"))

    def test_bad_account_rejected(self):
        led = CreditLedger()
        with self.assertRaises(CreditError):
            led.balance("   ")


if __name__ == "__main__":
    unittest.main()
