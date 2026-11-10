# DESIGN — GateFlat integration

Status: built + tested locally 10 Nov 2026. Off-chain half is built and
tested; onchain half is written but uncompiled and undeployed. Nothing
in this file claims a live chain interaction or a sent transaction.

## 1. The dispatch path (what the user sees)

```
agent drafts a call                user / agent framework
  { to, value, data, function?, code?, memo? }
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  gate_payload() — fail-closed, in order  │
  │  0. canonicalise + hash (robinhood.py)   │
  │  1. USDG credit check (credits.py)       │
  │     $WIF holder? → 0.005, else 0.01     │
  │  2. secret scan (scanner.py)             │
  │  3. policy scan, if code (policy.py)     │
  │  4. destination allow/block (robinhood)  │
  │  5. charge once + masked receipt         │
  │     + prepared onchain record            │
  └─────────────────────────────────────────┘
        │ ALLOW / HOLD / BLOCK
        ▼
  dispatch (user's wallet, later) OR stop
  prepared record → GateAudit.recordDecision (not deployed yet)
```

Decision precedence (first match wins): malformed → BLOCK; insufficient
credits → HOLD; secret LEAKED → BLOCK; policy BLOCKED → BLOCK;
destination BLOCK → BLOCK; secret REVIEW → HOLD; policy HELD → HOLD;
destination UNKNOWN → HOLD; otherwise ALLOW.

## 2. Module map

| Module | Origin | What it does |
|---|---|---|
| `scanner.py` | REUSED verbatim (hermes-secret-gate) | Secret patterns over canonical text |
| `policy.py` | REUSED verbatim (CageCheck) | Python policy engine (BLOCKED/HELD/OK) |
| `receipts.py` | REUSED verbatim (hermes-secret-gate) | Masked receipt ring (100 max) |
| `robinhood.py` | NEW | Chain constants, canonicalise/hash, verdict encoding, onchain-record builder, destination checks, live chain probe |
| `wif.py` | NEW | $WIF balanceOf read (eth_call, fail-soft), holder discount, flywheel status |
| `credits.py` | NEW | USDG demo ledger (Decimal, thread-locked, faucet) |
| `gate.py` | ADAPTED (from tapeout.py lineage) | Orchestration, fail-closed precedence, charge-once |
| `service.py` | NEW | Shared handler: local server + Vercel adapter |
| `server.py` | ADAPTED | Stdlib local server (thin wrapper) |
| `api/index.py` | NEW | Vercel WSGI adapter over service.handle |
| `tapeout.py` | CARRIED OVER, unused | TapeOut Gate integration layer — kept for reference; the live path does not call it |

## 3. The off-chain / onchain split (precise)

Off-chain (this repo, runs today): canonicalisation, hashing, secret
scan, policy scan, destination lists, USDG demo ledger, $WIF balance
read, receipts, and the *prepared* record. On-chain (designed, not
deployed): `GateAudit.recordDecision(payloadHash, verdict, rulesHash,
receiptId)` and `PolicyRegistry` (allow/block source of truth). The
contract stores the caller-supplied hash; it does not recompute it, so
there is no hash-algorithm mismatch between Python and Solidity. The
audit log is tamper-evident, NOT a proof that the scan ran — the honest
limit is stated in the contract README and the UI footer.

## 4. The $WIF read (rule 3) and the flywheel (rule 7)

- `wif.balance_of(address)` sends one `eth_call` to the Robinhood
  mainnet RPC: `balanceOf(address)` (selector 0x70a08231) against the
  $WIF token contract. Read-only; no wallet, no signing, no gas.
- Fail-soft: any failure (RPC down, bad address, bad token) returns
  `is_holder: False` with an error string. A failed probe means
  "unknown", never "holder".
- `run_cost_for`: holder → 0.005 USDG, else 0.01 USDG. The gate's
  credit check and its charge use the same price, so a discounted run
  is charged exactly once at the discounted price.
- The service caches a balance read for 30s per address so one gate
  run does not hammer the RPC.

## 5. The USDG ledger (honest limits)

Local, in-memory, demo-only. No real USDG moves, no token contract is
called, no wallet is connected, nothing is signed. Balances reset when
the server restarts; on Vercel serverless each warm instance holds its
own ledger. The demo faucet mints demo credit out of nothing and is
labelled DEMO in the UI and in every response. Money is Decimal, never
float.

## 6. Front-end — Flat Globe (Interactive 3D + Magnetic hover)

Style pick #5 per the permanent palette: one style (Interactive 3D /
Spatial Web, "Flat Globe" metaphor — a spinning flat-earth disc with a
glowing $WIF core), two animation techniques (3D tilt/rotation on the
globe, magnetic hover lift on buttons), transform + opacity only,
prefers-reduced-motion + a Low-motion toggle. See
`design/DESIGN_CONSTITUTION.md` + `design/DESIGN_REGISTRY.md`.
Panels: gate console, $WIF flywheel check, USDG credits + faucet,
recent receipts, live chain chip. The footer states the honest limits.

## 7. What is NEW for this event (rule 6 — port allowed)

Reused + labelled: scanner, policy, receipts (cores) and the two
contracts' shape. New in two days: robinhood.py, wif.py, credits.py,
gate.py adaptation, service.py, server adaptation, Vercel adapter,
Flat Globe front-end, all docs, and the submission narrative. The
TapeOut Gate source project stays untouched at its own repo and live
URL — this port does not break it.

## 8. What is NOT built (honest gaps)

- Contracts not compiled (no solc/Foundry in sandbox) and not deployed.
- No real transaction sent (needs the user's wallet; address not on
  file — see STATUS.md).
- $WIF token address unverified; $WIF live read timed out from this
  sandbox 10 Nov ~19:45 IST (transient — re-check on Vercel).
- No GitHub repo, no Vercel URL, no demo video, no submission yet.
