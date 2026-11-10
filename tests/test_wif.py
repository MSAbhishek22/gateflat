"""Tests for the $WIF integration (wif.py).

The live RPC call is mocked at the urllib layer, so tests run
offline. The holder test (balance > 0) and the fail-soft behaviour
are what matter; the token address itself is labelled UNVERIFIED in
the module docstring and is NOT asserted as correct here.
"""

import io
import json
import os
import sys
import unittest
from decimal import Decimal
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import robinhood  # noqa: E402
import wif  # noqa: E402
from wif import balance_of, flywheel, run_cost_for  # noqa: E402

HOLDER = "0x1111111111111111111111111111111111111111"
ZERO = "0x2222222222222222222222222222222222222222"


def _fake_urlopen(result_hex=None, error=None):
    """Build a urlopen mock returning one JSON-RPC response."""
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            if error is not None:
                return json.dumps(
                    {"jsonrpc": "2.0", "id": 1, "error": error}
                ).encode()
            return json.dumps(
                {"jsonrpc": "2.0", "id": 1, "result": result_hex}
            ).encode()

    return lambda req, timeout=None: FakeResp()


def _hex_balance(raw: int) -> str:
    return hex(raw)


class TestBalanceOf(unittest.TestCase):
    def test_holder_positive_balance(self):
        one_wif = 10 ** 18
        with patch.object(robinhood.urllib.request, "urlopen",
                          _fake_urlopen(_hex_balance(one_wif))):
            info = balance_of(HOLDER)
        self.assertTrue(info["is_holder"])
        self.assertEqual(info["balance_raw"], one_wif)
        self.assertEqual(info["balance_wif"], "1")
        self.assertIsNone(info["error"])
        self.assertFalse(info["token_verified"])  # labelled unverified

    def test_zero_balance_not_holder(self):
        with patch.object(robinhood.urllib.request, "urlopen",
                          _fake_urlopen(_hex_balance(0))):
            info = balance_of(ZERO)
        self.assertFalse(info["is_holder"])
        self.assertEqual(info["balance_wif"], "0")

    def test_rpc_error_is_fail_soft(self):
        with patch.object(
                robinhood.urllib.request, "urlopen",
                _fake_urlopen(error={"code": -32000, "message": "boom"})):
            info = balance_of(HOLDER)
        self.assertFalse(info["is_holder"])
        self.assertIsNone(info["balance_raw"])
        self.assertIsNotNone(info["error"])

    def test_network_down_is_fail_soft(self):
        with patch.object(robinhood.urllib.request, "urlopen",
                          side_effect=Exception("no route")):
            info = balance_of(HOLDER)
        self.assertFalse(info["is_holder"])
        self.assertIsNotNone(info["error"])

    def test_bad_address_rejected_without_rpc(self):
        with patch.object(robinhood.urllib.request, "urlopen",
                          side_effect=AssertionError("must not call")):
            info = balance_of("nope")
        self.assertFalse(info["is_holder"])
        self.assertIn("0x address", info["error"])

    def test_unknown_network_rejected(self):
        info = balance_of(HOLDER, network="moon")
        self.assertFalse(info["is_holder"])
        self.assertIn("unknown network", info["error"])

    def test_balance_uses_balanceof_selector(self):
        seen = {}

        def capture(req, timeout=None):
            seen["data"] = json.loads(req.data.decode())
            return _fake_urlopen(_hex_balance(5 * 10 ** 18))(req, timeout)

        with patch.object(robinhood.urllib.request, "urlopen", capture):
            balance_of(HOLDER)
        params = seen["data"]["params"][0]
        self.assertEqual(seen["data"]["method"], "eth_call")
        self.assertEqual(params["to"], wif.WIF_TOKEN)
        self.assertTrue(params["data"].startswith("0x70a08231"))
        self.assertIn(HOLDER[2:].lower(), params["data"])

    def test_balance_via_fallback_rpc(self):
        # The official RPC 403s (Vercel, 10 Nov) — the read must still
        # work when a fallback answers.
        with patch.object(
                wif, "rpc_call",
                return_value=(hex(2 * 10 ** 18),
                              "https://robinhood-rpc.publicnode.com")):
            info = balance_of(HOLDER)
        self.assertTrue(info["is_holder"])
        self.assertEqual(info["balance_wif"], "2")
        self.assertEqual(info["rpc_used"],
                         "https://robinhood-rpc.publicnode.com")


class TestFlywheel(unittest.TestCase):
    def test_holder_half_price(self):
        info = {"is_holder": True, "balance_wif": "2.5", "error": None}
        self.assertEqual(run_cost_for(info), Decimal("0.005"))
        fw = flywheel(info)
        self.assertEqual(fw["tier"], "holder")
        self.assertEqual(fw["discount"], "50%")

    def test_non_holder_full_price(self):
        info = {"is_holder": False, "balance_wif": "0", "error": None}
        self.assertEqual(run_cost_for(info), Decimal("0.01"))
        fw = flywheel(info)
        self.assertEqual(fw["tier"], "non_holder")
        self.assertEqual(fw["discount"], "0%")

    def test_probe_failure_is_unknown_full_price(self):
        info = {"is_holder": False, "balance_wif": None,
                "error": "boom"}
        self.assertEqual(run_cost_for(info), Decimal("0.01"))
        self.assertEqual(flywheel(info)["tier"], "unknown")


if __name__ == "__main__":
    unittest.main()
