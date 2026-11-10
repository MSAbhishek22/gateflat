"""Tests for the Robinhood Chain integration layer (robinhood.py).

Covers the pure functions (ported from tapeout.py), the network
constants (verified 10 Nov 2026), the onchain record's chain tag, and
the fail-soft live chain probe (mocked — no network in tests).
"""

import os
import sys
import time
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import robinhood
from robinhood import (
    MAINNET_CHAIN_ID,
    MAINNET_RPC,
    MAINNET_RPCS,
    MAINNET_RPC_FALLBACKS,
    TESTNET_CHAIN_ID,
    TESTNET_RPC,
    PayloadError,
    build_onchain_record,
    canonical_payload,
    chain_status,
    check_destination,
    encode_verdict,
    payload_hash,
    rpc_call,
    rules_hash,
    verdict_name,
)

TO = "0x1111111111111111111111111111111111111111"
TO2 = "0x2222222222222222222222222222222222222222"


class TestNetworkConstants(unittest.TestCase):
    def test_mainnet_chain_id(self):
        self.assertEqual(MAINNET_CHAIN_ID, 4663)
        self.assertEqual(MAINNET_RPC, "https://rpc.mainnet.chain.robinhood.com")

    def test_testnet_chain_id(self):
        self.assertEqual(TESTNET_CHAIN_ID, 46630)
        self.assertEqual(TESTNET_RPC, "https://rpc.testnet.chain.robinhood.com")

    def test_networks_table(self):
        self.assertEqual(robinhood.NETWORKS["mainnet"]["chain_id"], 4663)
        self.assertEqual(robinhood.NETWORKS["testnet"]["chain_id"], 46630)
        self.assertEqual(robinhood.NETWORKS["mainnet"]["gas_token"], "ETH")


class TestCanonicalPayload(unittest.TestCase):
    def test_canonical_is_deterministic(self):
        a = {"to": TO, "value": "0", "data": "0x"}
        b = {"data": "0x", "value": "0", "to": TO}
        self.assertEqual(canonical_payload(a), canonical_payload(b))

    def test_value_normalises_leading_zeroes(self):
        self.assertIn('"value":"0"', canonical_payload(
            {"to": TO, "value": "000", "data": "0x"}))

    def test_address_lowercased(self):
        out = canonical_payload(
            {"to": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
             "value": "0", "data": "0x"})
        self.assertIn("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", out)

    def test_missing_field_rejected(self):
        with self.assertRaises(PayloadError):
            canonical_payload({"to": TO, "value": "0"})

    def test_bad_address_rejected(self):
        with self.assertRaises(PayloadError):
            canonical_payload({"to": "not-an-address", "value": "0", "data": "0x"})

    def test_odd_hex_data_rejected(self):
        with self.assertRaises(PayloadError):
            canonical_payload({"to": TO, "value": "0", "data": "0x123"})

    def test_unknown_key_rejected(self):
        with self.assertRaises(PayloadError):
            canonical_payload({"to": TO, "value": "0", "data": "0x",
                               "surprise": True})

    def test_non_dict_rejected(self):
        with self.assertRaises(PayloadError):
            canonical_payload("nope")


class TestHashes(unittest.TestCase):
    def test_payload_hash_is_64_hex(self):
        h = payload_hash(canonical_payload({"to": TO, "value": "0", "data": "0x"}))
        self.assertEqual(len(h), 64)
        int(h, 16)  # must parse as hex

    def test_same_payload_same_hash(self):
        c = canonical_payload({"to": TO, "value": "0", "data": "0x"})
        self.assertEqual(payload_hash(c), payload_hash(c))

    def test_different_payload_different_hash(self):
        c1 = canonical_payload({"to": TO, "value": "0", "data": "0x"})
        c2 = canonical_payload({"to": TO, "value": "1", "data": "0x"})
        self.assertNotEqual(payload_hash(c1), payload_hash(c2))

    def test_rules_hash_order_independent(self):
        self.assertEqual(rules_hash(["b", "a"]), rules_hash(["a", "b"]))

    def test_rules_hash_empty_is_stable(self):
        self.assertEqual(rules_hash([]), rules_hash([]))


class TestVerdictEncoding(unittest.TestCase):
    def test_roundtrip(self):
        for word, code in (("ALLOW", 0), ("HOLD", 1), ("BLOCK", 2)):
            self.assertEqual(encode_verdict(word), code)
            self.assertEqual(verdict_name(code), word)

    def test_unknown_word_rejected(self):
        with self.assertRaises(PayloadError):
            encode_verdict("MAYBE")

    def test_unknown_code_rejected(self):
        with self.assertRaises(PayloadError):
            verdict_name(9)


class TestOnchainRecord(unittest.TestCase):
    def test_record_shape_matches_contract(self):
        rec = build_onchain_record("ab" * 32, "BLOCK",
                                   ["github_token"], "HSG-20261109-0001")
        self.assertEqual(rec["contract"], "GateAudit")
        self.assertEqual(rec["function"], "recordDecision")
        args = rec["args"]
        self.assertEqual(args["payloadHash"], "0x" + "ab" * 32)
        self.assertEqual(args["verdict"], 2)
        self.assertEqual(args["verdictName"], "BLOCK")
        self.assertTrue(args["rulesHash"].startswith("0x"))
        self.assertEqual(args["receiptId"], "HSG-20261109-0001")

    def test_record_tags_robinhood_chain(self):
        rec = build_onchain_record("ab" * 32, "ALLOW", [], "HSG-1")
        self.assertEqual(rec["chain"]["chainId"], 4663)
        self.assertEqual(rec["chain"]["name"], "Robinhood Chain")
        self.assertEqual(rec["chain"]["rpc"], MAINNET_RPC)

    def test_record_testnet_tag(self):
        rec = build_onchain_record("ab" * 32, "ALLOW", [], "HSG-1",
                                   network="testnet")
        self.assertEqual(rec["chain"]["chainId"], 46630)

    def test_bad_hash_rejected(self):
        with self.assertRaises(PayloadError):
            build_onchain_record("xyz", "ALLOW", [], "HSG-1")

    def test_empty_receipt_rejected(self):
        with self.assertRaises(PayloadError):
            build_onchain_record("ab" * 32, "ALLOW", [], "")

    def test_unknown_network_rejected(self):
        with self.assertRaises(PayloadError):
            build_onchain_record("ab" * 32, "ALLOW", [], "HSG-1",
                                 network="mars")


class TestDestination(unittest.TestCase):
    def test_allowlisted(self):
        self.assertEqual(check_destination(TO, [TO], [])[0], "ALLOW")

    def test_blocklisted(self):
        self.assertEqual(check_destination(TO, [], [TO])[0], "BLOCK")

    def test_block_wins_over_allow(self):
        self.assertEqual(check_destination(TO, [TO], [TO])[0], "BLOCK")

    def test_unknown_is_unknown(self):
        status, reason = check_destination(TO2, [TO], [])
        self.assertEqual(status, "UNKNOWN")
        self.assertIn("neither list", reason)


class TestChainStatus(unittest.TestCase):
    @patch("robinhood._rpc_call", side_effect=["0x1237", "0x69c8efb"])
    def test_mainnet_probe_success(self, _mock):
        st = chain_status("mainnet")
        self.assertTrue(st["reachable"])
        self.assertEqual(st["chain_id"], 4663)
        self.assertEqual(st["block_number"], 0x69C8EFB)
        self.assertTrue(st["chain_id_match"])
        self.assertEqual(st["rpc_used"], MAINNET_RPC)  # official first

    @patch("robinhood._rpc_call", side_effect=["0x1", "0x100"])
    def test_chain_id_mismatch_unreachable(self, _mock):
        st = chain_status("mainnet")
        self.assertFalse(st["reachable"])
        self.assertEqual(st["error"], "chain id mismatch")

    @patch("robinhood._rpc_call", side_effect=RuntimeError("boom"))
    def test_probe_failure_is_fail_soft(self, _mock):
        st = chain_status("mainnet")
        self.assertFalse(st["reachable"])
        self.assertIsNone(st["block_number"])
        self.assertIn("boom", st["error"])
        self.assertIsNone(st["rpc_used"])

    def test_unknown_network_fail_soft(self):
        st = chain_status("mars")
        self.assertFalse(st["reachable"])


class TestRpcFallback(unittest.TestCase):
    def test_fallback_answers_when_official_403s(self):
        err = urllib.error.HTTPError(
            MAINNET_RPC, 403, "Forbidden", {}, None)
        with patch("robinhood._rpc_call",
                   side_effect=[err, "0x1237"]) as mock_call:
            result, used = rpc_call("mainnet", "eth_chainId")
        self.assertEqual(result, "0x1237")
        self.assertEqual(used, MAINNET_RPC_FALLBACKS[0])
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(mock_call.call_args_list[0][0][0], MAINNET_RPC)

    @patch("robinhood._rpc_call", side_effect=[
        urllib.error.HTTPError(MAINNET_RPC, 403, "Forbidden", {}, None),
        "0x1237", "0x69c8efb"])
    def test_chain_status_reachable_via_fallback(self, _mock):
        st = chain_status("mainnet")
        self.assertTrue(st["reachable"])
        self.assertEqual(st["chain_id"], 4663)
        self.assertEqual(st["rpc_used"], MAINNET_RPC_FALLBACKS[0])

    @patch("robinhood._rpc_call", side_effect=RuntimeError("down"))
    def test_all_fallbacks_failing_raises_last_error(self, _mock):
        with self.assertRaises(RuntimeError):
            rpc_call("mainnet", "eth_chainId")
        self.assertEqual(_mock.call_count, len(MAINNET_RPCS))

    def test_expired_deadline_raises_without_calling(self):
        # A slow RPC must never make a gate run hang: once the
        # budget is gone, rpc_call stops without trying any URL.
        with patch("robinhood._rpc_call") as mock_call:
            with self.assertRaises(TimeoutError):
                rpc_call("mainnet", "eth_chainId",
                         deadline=time.monotonic() - 1)
        mock_call.assert_not_called()

    def test_deadline_caps_per_attempt_timeout(self):
        seen = []

        def capture(url, method, params, timeout):
            seen.append(timeout)
            raise RuntimeError("slow")

        with patch("robinhood._rpc_call", side_effect=capture):
            with self.assertRaises(RuntimeError):
                rpc_call("mainnet", "eth_chainId",
                         timeout=4.0,
                         deadline=time.monotonic() + 0.3)
        self.assertEqual(len(seen), len(MAINNET_RPCS))
        self.assertTrue(all(t <= 0.3 for t in seen))

    def test_chain_status_with_expired_deadline_is_fail_soft(self):
        status = chain_status("mainnet",
                              deadline=time.monotonic() - 1)
        self.assertFalse(status["reachable"])
        self.assertIn("budget", status["error"])

    def test_rpc_call_sends_real_user_agent(self):
        # The default "Python-urllib/3.x" UA is blocked outright by
        # several RPC front-doors (official RPC 403s Vercel with it).
        seen = {}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return b'{"jsonrpc":"2.0","id":1,"result":"0x1237"}'

        def capture(req, timeout=None):
            seen["ua"] = req.get_header("User-agent")
            return FakeResp()

        with patch.object(robinhood.urllib.request, "urlopen", capture):
            result, used = rpc_call("mainnet", "eth_chainId")
        self.assertEqual(result, "0x1237")
        self.assertIn("GateFlat", seen["ua"])
        self.assertNotIn("Python-urllib", seen["ua"])


if __name__ == "__main__":
    unittest.main()
