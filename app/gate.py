"""Gate orchestration — adapted 10 Nov 2026 from TapeOut Gate
(OKX X Layer) for GateFlat on Robinhood Chain.

Takes one agent-drafted contract-call payload and runs every check in
order, fail-closed, before anything is dispatched toward a Robinhood
Chain contract call:

  0. Canonicalise + hash the payload (robinhood.py). A malformed
     payload BLOCKs with a receipt and is never charged.
  1. USDG credit check (credits.py). An account that cannot afford
     one run HOLDs before any scan runs, so no work is done for free
     and no secret is ever scanned on credit. The credit pays for
     the evaluation itself. A $WIF holder's run costs half price
     (0.005 USDG — the $WIF flywheel, see wif.py); the check and the
     charge use the same discounted price.
  2. Secret-scan the canonical text (hermes-secret-gate scanner).
     A LEAKED verdict blocks; REVIEW holds.
  3. If the payload carries agent-drafted ``code``, run the CageCheck
     policy engine on it. BLOCKED blocks; HELD holds. Pure calldata
     payloads report policy ``not_applicable`` — the policy engine
     scans Python, and running it over hex calldata would be theatre.
  4. Check the destination against the allow/block lists. BLOCKED
     blocks; UNKNOWN holds; only an allowlisted destination allows.
  5. Charge one run of USDG demo credit, record a masked receipt
     (never contains secret material) and build the onchain record
     for GateAudit on Robinhood Chain.

Decision precedence (first match wins): malformed payload -> BLOCK;
insufficient credits -> HOLD; secret LEAKED -> BLOCK; policy BLOCKED
-> BLOCK; destination BLOCK -> BLOCK; secret REVIEW -> HOLD; policy
HELD -> HOLD; destination UNKNOWN -> HOLD; otherwise ALLOW.

Nothing here sends a transaction, calls an RPC, or contacts a chain
except the optional chain-status snapshot, which is a read-only probe
(see service.py). The ``onchain_record`` in the result is a *prepared*
call, not a sent one — see STATUS.md.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from credits import CreditLedger  # noqa: E402
from decimal import Decimal  # noqa: E402
from receipts import ReceiptStore  # noqa: E402
from robinhood import (  # noqa: E402
    PayloadError,
    build_onchain_record,
    canonical_payload,
    check_destination,
    payload_hash,
)
from scanner import scan_text  # noqa: E402
from policy import scan as policy_scan  # noqa: E402

DECISION_ALLOW = "ALLOW"
DECISION_HOLD = "HOLD"
DECISION_BLOCK = "BLOCK"

GATE_NAME = "gateflat"


def gate_payload(payload: dict, allowlist=(), blocklist=(),
                 store: ReceiptStore | None = None,
                 ledger: CreditLedger | None = None,
                 account: str | None = None,
                 network: str = "mainnet",
                 run_cost=None) -> dict:
    """Run the full gate on one payload dict. Never raises for a bad
    payload — a malformed payload is a BLOCK with a receipt, not an
    exception the caller can forget to handle.

    *run_cost* is the USDG price of this run (the $WIF holder price
    when a discount applied — see wif.py); None means the standard
    0.01 USDG. The credit check and the charge both use it, so a
    discounted run is charged the discounted price exactly once."""
    store = store or ReceiptStore()
    ledger = ledger or CreditLedger()
    account = account or "demo-agent-001"
    if run_cost is not None:
        run_cost = Decimal(run_cost)
    try:
        canonical = canonical_payload(payload)
    except PayloadError as exc:
        receipt = store.record(
            kind="gate_malformed", verdict="BLOCK",
            gate=GATE_NAME, findings=[{
                "rule": "malformed_payload", "line": 0,
                "masked": str(exc), "severity": "BLOCK",
            }],
        )
        return {
            "decision": DECISION_BLOCK,
            "reason": f"malformed payload: {exc}",
            "scan": None, "policy": None, "destination": None,
            "credits": ledger.snapshot(account, run_cost),
            "payload_hash": None, "receipt": receipt,
            "onchain_record": None,
        }

    # --- USDG credit gate: no scan runs on credit -----------------------
    # A $WIF holder's run costs less (wif.py); the check and the
    # charge below both use the same discounted price.
    if not ledger.can_afford(account, run_cost):
        cost = run_cost if run_cost is not None else ledger.run_cost
        receipt = store.record(
            kind="gate_decision", verdict="HOLD",
            gate=GATE_NAME, findings=[{
                "rule": "insufficient_usdg_credits", "line": 0,
                "masked": f"balance below one run cost ({cost} USDG)",
                "severity": "HOLD",
            }],
        )
        return {
            "decision": DECISION_HOLD,
            "reason": "insufficient USDG credits",
            "scan": None, "policy": None, "destination": None,
            "credits": ledger.snapshot(account, run_cost),
            "payload_hash": payload_hash(canonical),
            "receipt": receipt,
            "onchain_record": None,
        }

    phash = payload_hash(canonical)
    scan = scan_text(canonical)
    code = payload.get("code")
    if code:
        policy_verdict, policy_rule, policy_detail = policy_scan(code)
        policy = {"verdict": policy_verdict, "rule": policy_rule,
                  "detail": policy_detail}
    else:
        policy = {"verdict": "not_applicable", "rule": "no_code_field",
                  "detail": "Payload carries no agent-drafted code; "
                            "policy engine does not apply to calldata."}

    dest_status, dest_reason = check_destination(
        payload["to"], allowlist, blocklist)
    destination = {"status": dest_status, "reason": dest_reason}

    # --- decision, fail-closed, first match wins -------------------------
    if scan["verdict"] == "LEAKED":
        decision, reason = DECISION_BLOCK, "secret scan: LEAKED"
        rules = [f["rule"] for f in scan["findings"]]
    elif policy["verdict"] == "BLOCKED":
        decision, reason = DECISION_BLOCK, f"policy: {policy['rule']}"
        rules = [policy["rule"]]
    elif dest_status == "BLOCK":
        decision, reason = DECISION_BLOCK, dest_reason
        rules = ["destination_blocklisted"]
    elif scan["verdict"] == "REVIEW":
        decision, reason = DECISION_HOLD, "secret scan: REVIEW"
        rules = [f["rule"] for f in scan["findings"]]
    elif policy["verdict"] == "HELD":
        decision, reason = DECISION_HOLD, f"policy: {policy['rule']}"
        rules = [policy["rule"]]
    elif dest_status == "UNKNOWN":
        decision, reason = DECISION_HOLD, dest_reason
        rules = ["destination_unknown"]
    else:
        decision, reason = DECISION_ALLOW, "all checks passed"
        rules = []

    # --- charge one run (the evaluation ran, so it is paid for) ---------
    charged, new_balance, _ = ledger.charge(account, run_cost)

    receipt = store.record(
        kind="gate_decision", verdict=decision,
        gate=GATE_NAME, findings=scan["findings"],
    )
    onchain = build_onchain_record(phash, decision, rules,
                                   receipt["receipt_id"], network=network)
    return {
        "decision": decision,
        "reason": reason,
        "scan": scan,
        "policy": policy,
        "destination": destination,
        "credits": {
            **ledger.snapshot(account, run_cost),
            "charged_this_run": charged,
            "balance_after_usdg": str(new_balance),
            "wif_discount_applied": bool(
                run_cost is not None
                and run_cost < ledger.run_cost),
        },
        "payload_hash": phash,
        "receipt": receipt,
        "onchain_record": onchain,
    }
