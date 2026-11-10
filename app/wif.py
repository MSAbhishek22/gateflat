"""$WIF integration — NEW code, written 10 Nov 2026 for GateFlat
(World Is Flat Hackathon, rules 3 + 7).

Rule 3 requires the project to "use $wif onchain on Robinhood
Chain"; rule 7 requires a "$WIF flywheel". This module is the
read-only onchain half of both:

  - ``balance_of`` reads a wallet's $WIF balance with a single
    eth_call (ERC-20 ``balanceOf``) against the live Robinhood Chain
    RPC. Read-only, fail-soft, no wallet, no signing, no transaction.
  - ``run_cost_for`` / ``flywheel`` implement the discount: a $WIF
    holder pays half price (0.005 USDG instead of 0.01) per gate run.
    Holding $WIF makes the gate cheaper, so using the gate rewards
    holding $WIF — that is the flywheel. The discount is applied in
    the demo USDG ledger (credits.py); no real $WIF or USDG moves.

HONEST LIMITS — read before citing this as verified:
  - The $WIF token address below (RobinWifHat
    0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B) comes from a SECONDARY
    source only (a GitHub README, wif-desk). It was NOT verified on
    the official worldisflat.fun pages or on the Blockscout explorer
    at write time. If the address is wrong, ``balance_of`` returns
    an error (or a zero balance from a contract that is not $WIF)
    and the gate treats the caller as a non-holder — fail-soft, never
    a crash, never a fake holder status.
  - ``WIF_DECIMALS = 18`` is an ASSUMED ERC-20 default, unverified
    for this token. A wrong decimals value only mis-scales the
    displayed balance; the holder test (balance > 0) is unaffected.
  - A failed probe (RPC down, bad address, bad token) means
    "unknown", never "holder". The discount is earned only by a
    successful read of a positive balance.
  - No real transactions exist yet (rule 5): this module reads only.
    The onchain record the gate prepares is still a *prepared* call,
    not a sent one — see STATUS.md.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from decimal import Decimal

from robinhood import NETWORKS

# $WIF token — UNVERIFIED (secondary source only, see module docstring).
WIF_TOKEN = "0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B"
WIF_DECIMALS = 18  # assumed ERC-20 default; unverified for this token
WIF_SYMBOL = "$WIF"

# balanceOf(address) selector: first 4 bytes of keccak("balanceOf(address)").
_BALANCE_OF_SELECTOR = "0x70a08231"
_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Run costs (demo USDG ledger — see credits.py).
STANDARD_RUN_COST = Decimal("0.01")
HOLDER_RUN_COST = Decimal("0.005")  # 50% off for $WIF holders


def _eth_call(rpc_url: str, to: str, data: str,
              timeout: float = 5.0) -> str:
    """One eth_call. Returns the raw hex result, or raises on failure."""
    body = json.dumps({
        "jsonrpc": "2.0", "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"], "id": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        rpc_url, data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload["result"]


def balance_of(address: str, network: str = "mainnet",
               timeout: float = 5.0) -> dict:
    """Read a wallet's $WIF balance on Robinhood Chain. Fail-soft.

    Returns a dict: address, balance_raw (wei-style int or None),
    balance_wif (Decimal string or None), is_holder (bool — True only
    on a successful read of a positive balance), token, verified
    (whether the token address itself is verified — False, see
    module docstring), error (None on success).
    """
    if not isinstance(address, str) or not _ADDRESS_RE.match(address):
        return {"address": address, "balance_raw": None,
                "balance_wif": None, "is_holder": False,
                "token": WIF_TOKEN, "token_verified": False,
                "error": "address must be a 0x address (40 hex chars)"}
    if network not in NETWORKS:
        return {"address": address.lower(), "balance_raw": None,
                "balance_wif": None, "is_holder": False,
                "token": WIF_TOKEN, "token_verified": False,
                "error": f"unknown network: {network}"}
    data = _BALANCE_OF_SELECTOR + address[2:].lower().rjust(64, "0")
    try:
        raw_hex = _eth_call(NETWORKS[network]["rpc"], WIF_TOKEN, data,
                            timeout)
        raw = int(raw_hex, 16)
    except Exception as exc:  # noqa: BLE001 — fail-soft by design
        return {"address": address.lower(), "balance_raw": None,
                "balance_wif": None, "is_holder": False,
                "token": WIF_TOKEN, "token_verified": False,
                "error": str(exc)[:200]}
    balance = Decimal(raw) / Decimal(10 ** WIF_DECIMALS)
    return {"address": address.lower(), "balance_raw": raw,
            "balance_wif": str(balance), "is_holder": raw > 0,
            "token": WIF_TOKEN, "token_verified": False,
            "error": None}


def run_cost_for(balance_info: dict) -> Decimal:
    """Gate run cost for a wallet: half price for $WIF holders."""
    if balance_info and balance_info.get("is_holder"):
        return HOLDER_RUN_COST
    return STANDARD_RUN_COST


def flywheel(balance_info: dict) -> dict:
    """The $WIF flywheel, as a public status block for the API/UI.

    Holder: gate runs cost 0.005 USDG (50% off) — holding $WIF makes
    the gate cheaper, so every run rewards holding. Non-holder: full
    price, with the nudge to hold $WIF. Unknown (probe failed):
    full price, no claim either way.
    """
    holder = bool(balance_info and balance_info.get("is_holder"))
    cost = run_cost_for(balance_info)
    if balance_info and balance_info.get("error"):
        tier = "unknown"
        message = ("$WIF balance could not be read (chain or token "
                   "unreachable) — full price, no holder claim made.")
    elif holder:
        tier = "holder"
        message = (f"$WIF holder — gate runs cost {cost} USDG "
                   f"(50% off the {STANDARD_RUN_COST} USDG standard "
                   f"price). Holding $WIF makes the gate cheaper.")
    else:
        tier = "non_holder"
        message = (f"No $WIF held — gate runs cost {cost} USDG. Hold "
                   f"$WIF on Robinhood Chain to unlock the 50% "
                   f"holder price ({HOLDER_RUN_COST} USDG).")
    return {
        "token": WIF_TOKEN,
        "token_verified": False,
        "tier": tier,
        "is_holder": holder,
        "run_cost_usdg": str(cost),
        "standard_run_cost_usdg": str(STANDARD_RUN_COST),
        "discount": "50%" if holder else "0%",
        "balance_wif": (balance_info or {}).get("balance_wif"),
        "message": message,
    }
