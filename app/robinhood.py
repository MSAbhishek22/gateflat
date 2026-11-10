"""Robinhood Chain integration layer — NEW code, written 10 Nov 2026
for GateFlat (World Is Flat Hackathon).

Pure functions plus one fail-soft live chain probe. No wallet, no
signing, no private keys, no transactions sent. Everything except the
probe runs offline and is fully unit-tested.

Chain facts — VERIFIED 10 Nov 2026, consistent across Robinhood's own
docs (docs.robinhood.com/chain, robinhood.com support), QuickNode,
Tangem, Triport and viem chain definitions:
  - Mainnet chain ID 4663 (0x1237), RPC
    https://rpc.mainnet.chain.robinhood.com, explorer
    https://robinhoodchain.blockscout.com, gas ETH, Arbitrum Nitro L2.
    Mainnet live 1 Jul 2026.
  - Testnet chain ID 46630 (0xb626), RPC
    https://rpc.testnet.chain.robinhood.com, explorer
    https://explorer.testnet.chain.robinhood.com. Testnet live 10 Feb 2026.
  - USDG is the Paxos USD stablecoin and Robinhood Chain's native
    stablecoin (Robinhood docs). The USDG token contract address on
    Robinhood Chain is NOT verified — no address is stated anywhere in
    this module. GateFlat's USDG run credits are a local demo ledger
    (see credits.py); no real USDG ever moves.
  - Live probe verified 10 Nov 2026 from this sandbox: mainnet
    eth_chainId -> 0x1237, eth_blockNumber advancing, testnet
    eth_chainId -> 0xb626.

What this module does:
  1. Canonicalise an agent-drafted contract-call payload (``to`` /
     ``value`` / ``data`` / optional ``function`` + ``code``) into one
     deterministic JSON byte string.
  2. Hash it (SHA-256). Only the hash ever goes onchain — never the
     payload content, and never a secret. (The contract stores the
     caller-supplied hash; it does not recompute it, so there is no
     hash-algorithm mismatch between Python and Solidity to get wrong.
     The audit log is tamper-evident, NOT a proof that the scan ran —
     see DESIGN.md for the honest limit.)
  3. Encode the gate verdict as a uint8 for the contract
     (ALLOW=0, HOLD=1, BLOCK=2) and hash the fired rule ids.
  4. Build the exact record the contract's ``recordDecision`` call
     takes, tagged with the Robinhood Chain it targets, so a deploy
     step is mechanical.
  5. Check a destination address against a local allow/block sets.
     In production the onchain PolicyRegistry is the source of truth
     and this local copy is only a cache; an UNKNOWN destination is
     a HOLD, never an ALLOW.
  6. Probe the live chain (``chain_status``): eth_chainId +
     eth_blockNumber over JSON-RPC. Fail-soft — any failure returns
     reachable=False instead of raising.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request

VERDICT_ALLOW = 0
VERDICT_HOLD = 1
VERDICT_BLOCK = 2

_VERDICT_NAMES = {0: "ALLOW", 1: "HOLD", 2: "BLOCK"}

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_HEXDATA_RE = re.compile(r"^0x(?:[0-9a-fA-F]{2})*$")

# --- Robinhood Chain network constants (verified 10 Nov 2026) -----------
MAINNET_CHAIN_ID = 4663
MAINNET_CHAIN_ID_HEX = "0x1237"
MAINNET_RPC = "https://rpc.mainnet.chain.robinhood.com"
MAINNET_EXPLORER = "https://robinhoodchain.blockscout.com"
TESTNET_CHAIN_ID = 46630
TESTNET_CHAIN_ID_HEX = "0xb626"
TESTNET_RPC = "https://rpc.testnet.chain.robinhood.com"
TESTNET_EXPLORER = "https://explorer.testnet.chain.robinhood.com"
GAS_TOKEN = "ETH"
STABLECOIN = "USDG"  # Paxos USD stablecoin; native stablecoin of the chain.

# Fallback RPCs (public, no key) — added 10 Nov 2026 after the official
# RPC returned HTTP 403 to Vercel's servers and timed out from this
# sandbox. Sources: vectr.bot Robinhood Chain reference (secondary —
# the endpoints are public infrastructure, verified by calling them,
# not by the listing). The official RPC is always tried first; a
# fallback answers only when the official one fails. A fallback that
# answers is still the same chain (chainId is checked on every probe).
MAINNET_RPC_FALLBACKS = [
    "https://robinhood-rpc.publicnode.com",
    "https://robinhood.drpc.org",
    "https://rpc-robinhood.blockmachine.io",
]
MAINNET_RPCS = [MAINNET_RPC, *MAINNET_RPC_FALLBACKS]
TESTNET_RPCS = [TESTNET_RPC]

NETWORKS = {
    "mainnet": {
        "name": "Robinhood Chain",
        "chain_id": MAINNET_CHAIN_ID,
        "chain_id_hex": MAINNET_CHAIN_ID_HEX,
        "rpc": MAINNET_RPC,
        "rpcs": MAINNET_RPCS,
        "explorer": MAINNET_EXPLORER,
        "gas_token": GAS_TOKEN,
    },
    "testnet": {
        "name": "Robinhood Chain Testnet",
        "chain_id": TESTNET_CHAIN_ID,
        "chain_id_hex": TESTNET_CHAIN_ID_HEX,
        "rpc": TESTNET_RPC,
        "rpcs": TESTNET_RPCS,
        "explorer": TESTNET_EXPLORER,
        "gas_token": GAS_TOKEN,
    },
}


class PayloadError(ValueError):
    """Raised when an agent-drafted payload is malformed."""


def canonical_payload(payload: dict) -> str:
    """Validate *payload* and return its canonical JSON string.

    Required: ``to`` (0x + 40 hex chars), ``value`` (decimal string of
    a non-negative integer, wei), ``data`` (``0x`` or 0x + even hex).
    Optional: ``function`` (human-readable signature, e.g.
    ``transfer(address,uint256)``), ``code`` (agent-drafted script the
    policy engine may scan), ``memo`` (free text — scanned for secrets
    like everything else; never put a credential here).
    Unknown keys are rejected: a payload the gate cannot describe
    exactly is a payload the gate cannot approve.
    """
    if not isinstance(payload, dict):
        raise PayloadError("payload must be an object")
    allowed = {"to", "value", "data", "function", "code", "memo"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise PayloadError(f"unknown payload keys: {', '.join(unknown)}")
    for key in ("to", "value", "data"):
        if key not in payload:
            raise PayloadError(f"missing required field: {key}")
    to = payload["to"]
    if not isinstance(to, str) or not _ADDRESS_RE.match(to):
        raise PayloadError("'to' must be a 0x address (40 hex chars)")
    value = payload["value"]
    if not isinstance(value, str) or not value.isdigit():
        raise PayloadError("'value' must be a decimal string (wei)")
    data = payload["data"]
    if not isinstance(data, str) or not _HEXDATA_RE.match(data):
        raise PayloadError("'data' must be 0x hex (even length)")
    for key in ("function", "code", "memo"):
        if key in payload and not isinstance(payload[key], str):
            raise PayloadError(f"'{key}' must be a string")
    normalised = {
        "to": to.lower(),
        "value": str(int(value)),  # strips leading zeroes: one canonical form
        "data": data.lower(),
    }
    for key in ("function", "code", "memo"):
        if key in payload:
            normalised[key] = payload[key]
    return json.dumps(normalised, sort_keys=True, separators=(",", ":"))


def payload_hash(canonical: str) -> str:
    """SHA-256 hex of the canonical payload string (32 bytes)."""
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def rules_hash(rule_ids) -> str:
    """SHA-256 hex of the sorted, comma-joined fired rule ids."""
    joined = ",".join(sorted(set(rule_ids)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def encode_verdict(decision: str) -> int:
    """Map a gate decision word to its onchain uint8."""
    mapping = {"ALLOW": VERDICT_ALLOW, "HOLD": VERDICT_HOLD, "BLOCK": VERDICT_BLOCK}
    try:
        return mapping[decision]
    except KeyError:
        raise PayloadError(f"unknown decision: {decision!r}") from None


def verdict_name(code: int) -> str:
    """Map an onchain uint8 back to its decision word."""
    try:
        return _VERDICT_NAMES[code]
    except KeyError:
        raise PayloadError(f"unknown verdict code: {code!r}") from None


def build_onchain_record(payload_hash_hex: str, decision: str,
                         rule_ids, receipt_id: str,
                         network: str = "mainnet") -> dict:
    """Build the exact ``GateAudit.recordDecision`` argument set.

    Returns a plain dict — no signing, no transaction, no RPC. The
    deploy step takes this dict and sends it with the user's wallet;
    this module never touches a key. The record is tagged with the
    Robinhood Chain network it targets.
    """
    if network not in NETWORKS:
        raise PayloadError(f"unknown network: {network!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", payload_hash_hex or ""):
        raise PayloadError("payload_hash must be 64 lowercase hex chars")
    if not receipt_id or not isinstance(receipt_id, str):
        raise PayloadError("receipt_id must be a non-empty string")
    net = NETWORKS[network]
    return {
        "function": "recordDecision",
        "contract": "GateAudit",
        "chain": {
            "name": net["name"],
            "chainId": net["chain_id"],
            "rpc": net["rpc"],
            "explorer": net["explorer"],
        },
        "args": {
            "payloadHash": "0x" + payload_hash_hex,
            "verdict": encode_verdict(decision),
            "verdictName": decision,
            "rulesHash": "0x" + rules_hash(rule_ids),
            "receiptId": receipt_id,
        },
    }


def check_destination(to: str, allowlist, blocklist) -> tuple[str, str]:
    """Check *to* against local allow/block sets.

    Returns (status, reason) where status is ALLOW, BLOCK or UNKNOWN.
    An address on both lists is BLOCK (fail closed). An address on
    neither list is UNKNOWN (gate HOLDs it; only an explicit allowlist
    entry earns ALLOW).
    """
    addr = (to or "").lower()
    if addr in {b.lower() for b in blocklist}:
        return "BLOCK", "destination is blocklisted"
    if addr in {a.lower() for a in allowlist}:
        return "ALLOW", "destination is allowlisted"
    return "UNKNOWN", "destination is on neither list"


def _rpc_call(rpc_url: str, method: str, params=None,
              timeout: float = 4.0):
    """One JSON-RPC call against one URL. Returns the result, or raises
    on any failure (network error, timeout, or an error object)."""
    body = json.dumps(
        {"jsonrpc": "2.0", "method": method,
         "params": params if params is not None else [], "id": 1}
    ).encode("utf-8")
    req = urllib.request.Request(
        rpc_url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "error" in data:
        raise RuntimeError(str(data["error"]))
    return data["result"]


def rpc_call(network: str, method: str, params=None,
             timeout: float = 4.0) -> tuple:
    """One JSON-RPC call with fallback. Tries the official RPC first,
    then each public fallback in order, and returns
    ``(result, url_used)``. Raises the last error only when every URL
    failed, so a single failing endpoint never kills a read. Each
    attempt is bounded by *timeout* seconds."""
    urls = NETWORKS[network]["rpcs"]
    last_exc = RuntimeError("no RPC URL configured")
    for url in urls:
        try:
            return _rpc_call(url, method, params, timeout), url
        except Exception as exc:  # noqa: BLE001 — try the next URL
            last_exc = exc
    raise last_exc


def chain_status(network: str = "mainnet", timeout: float = 5.0) -> dict:
    """Probe the live Robinhood Chain. Fail-soft: never raises.

    Returns a dict with network, chain_id, block_number (ints when the
    probe succeeds, None when it does not), rpc, rpc_used (the URL
    that actually answered, or None), explorer and reachable. A failed
    probe means "chain unreachable from here", never "chain does not
    exist". The chainId is checked on every probe, so a fallback that
    answers for a different chain is rejected, not trusted."""
    if network not in NETWORKS:
        return {"network": network, "reachable": False,
                "error": f"unknown network: {network}"}
    net = NETWORKS[network]
    try:
        chain_hex, rpc_used = rpc_call(network, "eth_chainId",
                                       timeout=timeout)
        block_hex, _ = rpc_call(network, "eth_blockNumber",
                                timeout=timeout)
        chain_id = int(chain_hex, 16)
        block = int(block_hex, 16)
        ok = chain_id == net["chain_id"]
        return {
            "network": network,
            "name": net["name"],
            "chain_id": chain_id,
            "chain_id_hex": chain_hex,
            "expected_chain_id": net["chain_id"],
            "chain_id_match": ok,
            "block_number": block,
            "block_number_hex": block_hex,
            "rpc": net["rpc"],
            "rpc_used": rpc_used,
            "explorer": net["explorer"],
            "reachable": ok,
            "error": None if ok else "chain id mismatch",
        }
    except Exception as exc:  # noqa: BLE001 — fail-soft by design
        return {
            "network": network,
            "name": net["name"],
            "chain_id": None,
            "chain_id_hex": None,
            "expected_chain_id": net["chain_id"],
            "chain_id_match": False,
            "block_number": None,
            "block_number_hex": None,
            "rpc": net["rpc"],
            "rpc_used": None,
            "explorer": net["explorer"],
            "reachable": False,
            "error": str(exc)[:200],
        }
