"""TapeOut / X Layer integration layer — NEW code, written 9 Nov 2026.

Pure functions only: no network, no wallet, no signing, no RPC calls.
Everything here can run offline and is fully unit-tested. The onchain
half (contracts/GateAudit.sol, contracts/PolicyRegistry.sol) is NOT yet
deployed anywhere — see STATUS.md. Nothing in this module claims a live
chain interaction.

What this module does:
  1. Canonicalise an agent-drafted contract-call payload (``to`` /
     ``value`` / ``data`` / optional ``function`` + ``code``) into one
     deterministic JSON byte string.
  2. Hash it (SHA-256). Only the hash ever goes onchain — never the
     payload content, and never a secret. (The contract stores the
     caller-supplied hash; it does not recompute it, so there is no
     hash-algorithm mismatch between Python and Solidity to get wrong.
     The audit log is tamper-evident, NOT a proof that the scan ran —
     see DESIGN.md §6 for the honest limit.)
  3. Encode the gate verdict as a uint8 for the contract
     (ALLOW=0, HOLD=1, BLOCK=2) and hash the fired rule ids.
  4. Build the exact record the contract's ``recordDecision`` call
     takes, so the Week-2 deploy step is mechanical.
  5. Check a destination address against a local allowlist/blocklist
     snapshot. In production the onchain PolicyRegistry is the source
     of truth and this local copy is only a cache; an UNKNOWN
     destination is a HOLD, never an ALLOW.
"""

from __future__ import annotations

import hashlib
import json
import re

VERDICT_ALLOW = 0
VERDICT_HOLD = 1
VERDICT_BLOCK = 2

_VERDICT_NAMES = {0: "ALLOW", 1: "HOLD", 2: "BLOCK"}

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_HEXDATA_RE = re.compile(r"^0x(?:[0-9a-fA-F]{2})*$")


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
                         rule_ids, receipt_id: str) -> dict:
    """Build the exact ``GateAudit.recordDecision`` argument set.

    Returns a plain dict — no signing, no transaction, no RPC. The
    Week-2 deploy step takes this dict and sends it with the user's
    wallet; this module never touches a key.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", payload_hash_hex or ""):
        raise PayloadError("payload_hash must be 64 lowercase hex chars")
    if not receipt_id or not isinstance(receipt_id, str):
        raise PayloadError("receipt_id must be a non-empty string")
    return {
        "function": "recordDecision",
        "contract": "GateAudit",
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
