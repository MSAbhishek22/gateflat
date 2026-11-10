"""Tests for the gate orchestration (gate.py) — adapted 10 Nov 2026
for GateFlat: Robinhood Chain records + USDG credit gating.

Covers the fail-closed decision precedence, the credit check running
before any scan, and the guarantee that receipts never carry secret
material.
"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from credits import CreditLedger
from gate import gate_payload
from receipts import ReceiptStore

TO = "0x1111111111111111111111111111111111111111"
BAD = "0x2222222222222222222222222222222222222222"
GH_TOKEN = "ghp_" + "A" * 36  # synthetic fixture, matches the scanner rule


def clean_payload(**over):
    p = {"to": TO, "value": "0", "data": "0x", "function": "ping()"}
    p.update(over)
    return p


class TestDecisions(unittest.TestCase):
    def test_allowlisted_clean_payload_allows(self):
        r = gate_payload(clean_payload(), allowlist=[TO])
        self.assertEqual(r["decision"], "ALLOW")
        self.assertEqual(r["onchain_record"]["args"]["verdict"], 0)
        self.assertEqual(r["onchain_record"]["chain"]["chainId"], 4663)

    def test_unknown_destination_holds(self):
        # Fail-closed default: no lists at all -> HOLD, never ALLOW.
        r = gate_payload(clean_payload())
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(r["reason"], "destination is on neither list")

    def test_blocklisted_destination_blocks(self):
        r = gate_payload(clean_payload(to=BAD), allowlist=[TO], blocklist=[BAD])
        self.assertEqual(r["decision"], "BLOCK")

    def test_leaked_secret_blocks(self):
        r = gate_payload(clean_payload(memo="token " + GH_TOKEN),
                         allowlist=[TO])
        self.assertEqual(r["decision"], "BLOCK")
        self.assertEqual(r["scan"]["verdict"], "LEAKED")
        self.assertEqual(r["onchain_record"]["args"]["verdict"], 2)

    def test_secret_never_in_receipt_or_record(self):
        r = gate_payload(clean_payload(memo="token " + GH_TOKEN),
                         allowlist=[TO])
        blob = str(r["receipt"]) + str(r["onchain_record"])
        self.assertNotIn(GH_TOKEN, blob)
        self.assertNotIn("A" * 36, blob)

    def test_policy_blocked_code_blocks(self):
        r = gate_payload(
            clean_payload(code="import subprocess\nsubprocess.run(['ls'])"),
            allowlist=[TO])
        self.assertEqual(r["decision"], "BLOCK")
        self.assertEqual(r["policy"]["verdict"], "BLOCKED")

    def test_policy_held_code_holds(self):
        r = gate_payload(clean_payload(code="import socket\nprint('hi')"),
                         allowlist=[TO])
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(r["policy"]["verdict"], "HELD")

    def test_no_code_field_is_not_applicable(self):
        r = gate_payload(clean_payload(), allowlist=[TO])
        self.assertEqual(r["policy"]["verdict"], "not_applicable")

    def test_malformed_payload_blocks_not_raises(self):
        r = gate_payload({"to": "nope", "value": "0", "data": "0x"})
        self.assertEqual(r["decision"], "BLOCK")
        self.assertIsNone(r["payload_hash"])
        self.assertIsNone(r["onchain_record"])

    def test_receipt_and_record_agree(self):
        r = gate_payload(clean_payload(), allowlist=[TO])
        self.assertEqual(r["onchain_record"]["args"]["receiptId"],
                         r["receipt"]["receipt_id"])
        self.assertEqual(r["onchain_record"]["args"]["payloadHash"],
                         "0x" + r["payload_hash"])

    def test_receipts_accumulate_in_store(self):
        store = ReceiptStore()
        gate_payload(clean_payload(), allowlist=[TO], store=store)
        gate_payload(clean_payload(), allowlist=[TO], store=store)
        self.assertEqual(len(store.list_recent(10)), 2)


class TestCredits(unittest.TestCase):
    def test_allow_charges_one_run(self):
        ledger = CreditLedger()
        r = gate_payload(clean_payload(), allowlist=[TO], ledger=ledger)
        self.assertEqual(r["decision"], "ALLOW")
        self.assertTrue(r["credits"]["charged_this_run"])
        self.assertEqual(r["credits"]["balance_after_usdg"], "9.99")
        self.assertEqual(ledger.balance("demo-agent-001"), Decimal("9.99"))

    def test_block_still_charges_evaluation(self):
        ledger = CreditLedger()
        r = gate_payload(clean_payload(memo="token " + GH_TOKEN),
                         allowlist=[TO], ledger=ledger)
        self.assertEqual(r["decision"], "BLOCK")
        self.assertTrue(r["credits"]["charged_this_run"])

    def test_insufficient_credits_holds_before_scan(self):
        ledger = CreditLedger(start_balance=Decimal("0.00"))
        r = gate_payload(clean_payload(memo="token " + GH_TOKEN),
                         allowlist=[TO], ledger=ledger)
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(r["reason"], "insufficient USDG credits")
        self.assertIsNone(r["scan"])  # no scan ran on credit
        self.assertIsNone(r["onchain_record"])
        self.assertEqual(ledger.balance("demo-agent-001"), Decimal("0.00"))

    def test_malformed_payload_is_never_charged(self):
        ledger = CreditLedger()
        r = gate_payload({"to": "nope", "value": "0", "data": "0x"},
                         ledger=ledger)
        self.assertEqual(r["decision"], "BLOCK")
        self.assertEqual(ledger.balance("demo-agent-001"), Decimal("10.00"))

    def test_top_up_unblocks(self):
        ledger = CreditLedger(start_balance=Decimal("0.00"))
        ledger.top_up("demo-agent-001")
        r = gate_payload(clean_payload(), allowlist=[TO], ledger=ledger)
        self.assertEqual(r["decision"], "ALLOW")


class TestWifDiscount(unittest.TestCase):
    def test_holder_run_costs_half(self):
        ledger = CreditLedger()
        r = gate_payload(clean_payload(), allowlist=[TO], ledger=ledger,
                         run_cost=Decimal("0.005"))
        self.assertEqual(r["decision"], "ALLOW")
        self.assertTrue(r["credits"]["wif_discount_applied"])
        self.assertEqual(r["credits"]["run_cost_usdg"], "0.005")
        self.assertEqual(r["credits"]["balance_after_usdg"], "9.995")

    def test_holder_price_affords_what_standard_cannot(self):
        # 0.008 USDG cannot afford the 0.01 standard run, but can
        # afford the 0.005 holder run.
        ledger = CreditLedger(start_balance=Decimal("0.008"))
        r = gate_payload(clean_payload(), allowlist=[TO], ledger=ledger,
                         run_cost=Decimal("0.005"))
        self.assertEqual(r["decision"], "ALLOW")

    def test_standard_price_still_holds_at_0008(self):
        ledger = CreditLedger(start_balance=Decimal("0.008"))
        r = gate_payload(clean_payload(), allowlist=[TO], ledger=ledger)
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(r["reason"], "insufficient USDG credits")


if __name__ == "__main__":
    unittest.main()
