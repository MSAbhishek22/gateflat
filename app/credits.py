"""USDG run credits — NEW code, written 10 Nov 2026 for GateFlat.

A local, in-memory demo ledger. Every gate evaluation costs a small
USDG-denominated fee; an account with too little credit gets HOLDed
before the scan runs, so no work is done for free and no secret is
ever scanned on credit.

HONEST LIMITS — read before citing this as a payment system:
  - This ledger is LOCAL and DEMO-ONLY. No real USDG moves, no token
    contract is called, no wallet is connected, nothing is signed.
    The USDG token contract address on Robinhood Chain is unverified
    and is not referenced anywhere here.
  - Balances live in process memory and reset when the server
    restarts (same as the receipt ring). On Vercel serverless, each
    warm instance holds its own ledger; the balance the UI shows is
    the balance of the instance that answered.
  - The demo faucet (top_up) mints demo credit out of nothing. It is
    labelled DEMO in the UI and in every response.
  - Money is Decimal, never float. Amounts are USDG with 2 decimal
    places for display; the ledger stores Decimal exactly.
"""

from __future__ import annotations

import threading
from decimal import Decimal

DEFAULT_START_BALANCE = Decimal("10.00")  # USDG, demo credit per new account
RUN_COST = Decimal("0.01")  # USDG per gate evaluation
FAUCET_AMOUNT = Decimal("10.00")  # USDG per demo top-up
CURRENCY = "USDG"


class CreditError(ValueError):
    """Raised for malformed credit requests (bad account, bad amount)."""


def _normalise_account(account) -> str:
    if account is None:
        return "demo-agent-001"
    if not isinstance(account, str) or not account.strip():
        raise CreditError("account must be a non-empty string")
    return account.strip()[:64]


class CreditLedger:
    """In-memory USDG credit ledger (demo only — see module docstring)."""

    def __init__(self, start_balance=DEFAULT_START_BALANCE,
                 run_cost=RUN_COST):
        self._balances: dict[str, Decimal] = {}
        self._start = Decimal(start_balance)
        self._cost = Decimal(run_cost)
        self._lock = threading.Lock()

    @property
    def run_cost(self) -> Decimal:
        return self._cost

    def balance(self, account) -> Decimal:
        """Current balance; a new account starts at the demo balance."""
        acct = _normalise_account(account)
        return self._balances.get(acct, self._start)

    def can_afford(self, account, cost=None) -> bool:
        return self.balance(account) >= self._cost_for(cost)

    def charge(self, account, cost=None) -> tuple[bool, Decimal, str]:
        """Charge one run at *cost* (default the ledger's run cost).
        Returns (ok, new_balance, reason).

        Returns ok=False and charges nothing when the balance is too
        low. Never lets a balance go negative. The $WIF holder
        discount passes its lower cost in here (see wif.py)."""
        acct = _normalise_account(account)
        amount = self._cost_for(cost)
        with self._lock:
            bal = self._balances.get(acct, self._start)
            if bal < amount:
                return False, bal, "insufficient USDG credits"
            new_bal = bal - amount
            self._balances[acct] = new_bal
        return True, new_bal, "charged"

    def _cost_for(self, cost) -> Decimal:
        if cost is None:
            return self._cost
        value = Decimal(cost)
        if value <= 0:
            raise CreditError("run cost must be positive")
        return value

    def top_up(self, account, amount=FAUCET_AMOUNT) -> tuple[Decimal, str]:
        """Demo faucet: add demo USDG out of nothing. Labelled DEMO."""
        acct = _normalise_account(account)
        amt = Decimal(amount)
        if amt <= 0:
            raise CreditError("top-up amount must be positive")
        with self._lock:
            new_bal = self._balances.get(acct, self._start) + amt
            self._balances[acct] = new_bal
        return new_bal, "demo faucet top-up (no real USDG moved)"

    def snapshot(self, account, cost=None) -> dict:
        """Public balance view for the API/UI.

        *cost* is the run cost actually charged for this account's
        run (the $WIF holder price when a discount applied); when
        omitted the ledger's standard run cost is shown."""
        bal = self.balance(account)
        shown_cost = self._cost_for(cost)
        return {
            "account": _normalise_account(account),
            "balance_usdg": str(bal),
            "run_cost_usdg": str(shown_cost),
            "runs_remaining": int(bal // shown_cost),
            "currency": CURRENCY,
            "demo": True,
            "note": "Demo ledger only — no real USDG moves.",
        }
