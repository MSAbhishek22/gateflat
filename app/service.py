"""Shared request handling for GateFlat — NEW code, written 10 Nov 2026.

One function, ``handle(method, path, query, body_bytes)``, serves
every route. The local stdlib server (server.py) and the Vercel WSGI
adapter (api/index.py) both call it, so local and deployed behaviour
cannot drift apart.

State is module-level and in-memory by design: the receipt ring
(ReceiptStore, 100 max) and the USDG demo ledger (CreditLedger).
On Vercel serverless each warm instance holds its own copy; nothing
here needs cross-request persistence beyond what the response itself
carries, because every gate result returns its receipt, its credit
balance and its prepared onchain record in the response body.

Demo allowlist: one clearly-labelled demo contract address is
allowlisted so the ALLOW path is reachable in the UI. It is NOT a
real deployment — the UI and /api/health label it as demo.
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from credits import CreditLedger  # noqa: E402
from gate import gate_payload  # noqa: E402
from receipts import ReceiptStore  # noqa: E402
from robinhood import chain_status  # noqa: E402
from wif import balance_of, flywheel, run_cost_for  # noqa: E402

STORE = ReceiptStore()
LEDGER = CreditLedger()
ALLOWLIST: set = set()
BLOCKLIST: set = set()

# Demo contract: allowlisted so ALLOW is reachable in the demo. NOT a
# real deployment; labelled as demo everywhere it appears.
DEMO_CONTRACT = "0x1111111111111111111111111111111111111111"
ALLOWLIST.add(DEMO_CONTRACT.lower())

MAX_BODY = 64 * 1024
_CHAIN_CACHE: dict = {}
_CHAIN_CACHE_TTL = 30.0
_WIF_CACHE: dict = {}


def _cached_chain(network: str, deadline: float | None = None) -> dict:
    now = time.time()
    hit = _CHAIN_CACHE.get(network)
    if hit and now - hit[0] < _CHAIN_CACHE_TTL:
        return hit[1]
    status = chain_status(network, deadline=deadline)
    _CHAIN_CACHE[network] = (now, status)
    return status


def _cached_wif(address: str, network: str,
                deadline: float | None = None) -> dict:
    """$WIF balance, cached 30s per address so one gate run does not
    hammer the RPC. A failed probe is cached too (as unknown)."""
    key = (network, address.lower())
    now = time.time()
    hit = _WIF_CACHE.get(key)
    if hit and now - hit[0] < _CHAIN_CACHE_TTL:
        return hit[1]
    info = balance_of(address, network, deadline=deadline)
    _WIF_CACHE[key] = (now, info)
    return info


def _json(status: int, obj: dict) -> tuple[int, str, bytes]:
    return status, "application/json", json.dumps(obj).encode("utf-8")


def _html(body: bytes) -> tuple[int, str, bytes]:
    return 200, "text/html; charset=utf-8", body


def handle(method: str, path: str, query: dict | None = None,
           body: bytes | None = None) -> tuple[int, str, bytes]:
    """Route one request. Returns (status, content_type, body_bytes)."""
    query = query or {}
    # One time budget per request for every RPC probe in it (chain
    # status + $WIF read). Found 10 Nov ~20:45 IST: with a slow RPC
    # the two probes could burn 4s x 4 fallbacks x 2 calls = 48s and
    # the gate endpoint hung past a 40s client timeout. With the
    # budget the gate still decides (full price, chain "unreachable")
    # instead of hanging — a slow chain never blocks a gate run.
    deadline = time.monotonic() + 10.0
    if method == "GET" and path in ("/", "/index.html"):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "index.html"), "rb") as fh:
            return _html(fh.read())

    if method == "GET" and path == "/api/health":
        return _json(200, {
            "status": "ok",
            "gate": "gateflat",
            "chain": _cached_chain("mainnet", deadline),
            "onchain": "not_deployed",
            "demo_allowlist": [DEMO_CONTRACT],
            "credits_demo": True,
        })

    if method == "GET" and path == "/api/chain":
        network = (query.get("network") or ["mainnet"])[0]
        return _json(200, _cached_chain(network, deadline))

    if method == "GET" and path == "/api/wif":
        address = (query.get("address") or [""])[0]
        network = (query.get("network") or ["mainnet"])[0]
        if not address:
            return _json(400, {"error": "address query param required"})
        info = _cached_wif(address, network, deadline)
        if info.get("error") and info.get("balance_raw") is None \
                and "must be a 0x address" in info["error"]:
            return _json(400, {"error": info["error"]})
        return _json(200, {**info, "flywheel": flywheel(info)})

    if method == "GET" and path == "/api/credits":
        account = (query.get("account") or ["demo-agent-001"])[0]
        return _json(200, LEDGER.snapshot(account))

    if method == "GET" and path == "/api/receipts":
        try:
            limit = int((query.get("limit") or ["10"])[0])
        except ValueError:
            limit = 10
        return _json(200, {"receipts": STORE.list_recent(limit)})

    if method == "POST" and path == "/api/credits/topup":
        data = _parse_body(body)
        if isinstance(data, tuple):
            return data
        try:
            new_bal, note = LEDGER.top_up(data.get("account"))
        except Exception as exc:  # noqa: BLE001 — bad input, report it
            return _json(400, {"error": str(exc)})
        return _json(200, {
            "account": (data.get("account") or "demo-agent-001"),
            "balance_usdg": str(new_bal),
            "note": note,
            "demo": True,
        })

    if method == "POST" and path == "/api/gate":
        data = _parse_body(body)
        if isinstance(data, tuple):
            return data
        if not isinstance(data, dict):
            return _json(400, {"error": "body must be a JSON object"})
        account = data.pop("account", None) or "demo-agent-001"
        network = data.pop("network", None) or "mainnet"
        # $WIF flywheel: an optional wif_address earns the holder
        # discount on this run. The probe is fail-soft — a failed
        # read means full price, never a fake holder status.
        wif_info = None
        run_cost = None
        wif_address = data.pop("wif_address", None)
        if wif_address:
            wif_info = _cached_wif(str(wif_address), network, deadline)
            run_cost = run_cost_for(wif_info)
        result = gate_payload(data, ALLOWLIST, BLOCKLIST, STORE,
                              LEDGER, account, network, run_cost)
        result["chain"] = _cached_chain(network, deadline)
        if wif_info is not None:
            result["wif"] = flywheel(wif_info)
        return _json(200, result)

    return _json(404, {"error": "not found"})


def _parse_body(body: bytes | None):
    """Parse a JSON request body. Returns dict, or an error tuple."""
    if body is None:
        return {}
    if len(body) > MAX_BODY:
        return _json(413, {"error": "payload too large (64 KiB max)"})
    try:
        data = json.loads(body or b"{}")
    except json.JSONDecodeError:
        return _json(400, {"error": "body is not valid JSON"})
    return data
