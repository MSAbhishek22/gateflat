"""Tests for the shared request handler (service.py) + local server.

service.handle is what both the local stdlib server and the Vercel
WSGI adapter call. The live-chain probe is patched out here so tests
run offline; the probe itself is covered in test_robinhood.py.
"""

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import server as server_mod  # noqa: E402
import service  # noqa: E402

FAKE_CHAIN = {
    "network": "mainnet",
    "name": "Robinhood Chain",
    "chain_id": 4663,
    "chain_id_hex": "0x1237",
    "expected_chain_id": 4663,
    "chain_id_match": True,
    "block_number": 111092731,
    "block_number_hex": "0x69c8efb",
    "rpc": "https://rpc.mainnet.chain.robinhood.com",
    "explorer": "https://robinhoodchain.blockscout.com",
    "reachable": True,
    "error": None,
}

TO = "0x1111111111111111111111111111111111111111"


class TestServiceHandle(unittest.TestCase):
    def setUp(self):
        self._patch = patch.object(service, "chain_status",
                                   return_value=dict(FAKE_CHAIN))
        self._patch.start()
        service._CHAIN_CACHE.clear()
        service._WIF_CACHE.clear()

    def tearDown(self):
        self._patch.stop()
        service._CHAIN_CACHE.clear()
        service._WIF_CACHE.clear()

    def test_health(self):
        status, ctype, body = service.handle("GET", "/api/health")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["gate"], "gateflat")
        self.assertEqual(data["onchain"], "not_deployed")
        self.assertTrue(data["chain"]["reachable"])
        self.assertEqual(data["chain"]["chain_id"], 4663)

    def test_chain_endpoint(self):
        status, _, body = service.handle("GET", "/api/chain",
                                         {"network": ["mainnet"]})
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["block_number"], 111092731)

    def test_gate_allow_demo_contract(self):
        # The demo contract is allowlisted in service.py, so a clean
        # payload to it ALLOWs (and charges 0.01 demo USDG).
        payload = json.dumps({"to": TO, "value": "0", "data": "0x",
                              "account": "svc-test-1"}).encode()
        status, _, body = service.handle("POST", "/api/gate", {}, payload)
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["decision"], "ALLOW")
        self.assertEqual(data["chain"]["chain_id"], 4663)
        self.assertIn("receipt", data)

    def test_gate_bad_json_400(self):
        status, _, body = service.handle("POST", "/api/gate", {}, b"{not json")
        self.assertEqual(status, 400)
        self.assertIn("not valid JSON", body.decode())

    def test_credits_and_topup(self):
        status, _, body = service.handle(
            "GET", "/api/credits", {"account": ["svc-test-2"]})
        self.assertEqual(json.loads(body)["balance_usdg"], "10.00")
        payload = json.dumps({"account": "svc-test-2"}).encode()
        status, _, body = service.handle("POST", "/api/credits/topup",
                                         {}, payload)
        self.assertEqual(json.loads(body)["balance_usdg"], "20.00")

    def test_receipts_endpoint(self):
        status, _, body = service.handle("GET", "/api/receipts",
                                         {"limit": ["5"]})
        self.assertEqual(status, 200)
        self.assertIn("receipts", json.loads(body))

    def test_unknown_route_404(self):
        status, _, _ = service.handle("GET", "/nope")
        self.assertEqual(status, 404)

    def test_wif_endpoint_holder(self):
        info = {"address": TO, "balance_raw": 10 ** 18,
                "balance_wif": "1", "is_holder": True,
                "token": "0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B",
                "token_verified": False, "error": None}
        with patch.object(service, "balance_of", return_value=dict(info)):
            status, _, body = service.handle(
                "GET", "/api/wif", {"address": [TO]})
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(data["is_holder"])
        self.assertEqual(data["flywheel"]["tier"], "holder")
        self.assertEqual(data["flywheel"]["run_cost_usdg"], "0.005")

    def test_wif_endpoint_missing_address_400(self):
        status, _, _ = service.handle("GET", "/api/wif", {})
        self.assertEqual(status, 400)

    def test_gate_with_wif_holder_charges_half(self):
        info = {"address": TO, "balance_raw": 10 ** 18,
                "balance_wif": "1", "is_holder": True,
                "token": "0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B",
                "token_verified": False, "error": None}
        payload = json.dumps({"to": TO, "value": "0", "data": "0x",
                              "account": "svc-wif-1",
                              "wif_address": TO}).encode()
        with patch.object(service, "balance_of", return_value=dict(info)):
            status, _, body = service.handle("POST", "/api/gate", {},
                                             payload)
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["decision"], "ALLOW")
        self.assertTrue(data["credits"]["wif_discount_applied"])
        self.assertEqual(data["credits"]["balance_after_usdg"], "9.995")
        self.assertEqual(data["wif"]["tier"], "holder")


class TestLiveServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._patch = patch.object(service, "chain_status",
                                  return_value=dict(FAKE_CHAIN))
        cls._patch.start()
        service._CHAIN_CACHE.clear()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server_mod.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls._patch.stop()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_health_over_http(self):
        with urllib.request.urlopen(self.url("/api/health")) as resp:
            body = json.loads(resp.read())
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["gate"], "gateflat")

    def test_gate_bad_json_400_over_http(self):
        req = urllib.request.Request(
            self.url("/api/gate"), data=b"{not json",
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 400)


if __name__ == "__main__":
    unittest.main()
