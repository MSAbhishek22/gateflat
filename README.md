# GateFlat — the $WIF gate on Robinhood Chain

**Event:** World Is Flat Hackathon (Robinhood Chain) · **$10,000 USDG winner-take-all** ·
**deadline Thu 12 Nov 2026 23:00 IST** (17:30 UTC) · solo, online, free, port/existing work allowed.

**One-line pitch:** before an agent's drafted contract call reaches Robinhood Chain, it crosses
this gate — secrets get stopped, destinations get checked, every decision leaves a masked receipt
and a prepared onchain record, and $WIF holders run the gate at half price.

## Status — 10 Nov 2026: BUILD (local, tested, not yet live)

| Piece | State |
|---|---|
| Research (official worldisflat.fun pages + Robinhood Chain docs) | Done — see RESEARCH.md |
| Gate core (scanner / policy / receipts) | Ported verbatim from hermes-secret-gate + CageCheck, **108/108 tests PASS** (Python 3.12, unittest, Linux sandbox) |
| Robinhood integration (`app/robinhood.py`, `app/wif.py`, `app/credits.py`, `app/gate.py`, `app/service.py`) | Written, tested, live chain probe verified 10 Nov ~19:25 IST, then RPC timed out from sandbox ~19:45 IST (transient — fail-soft, see STATUS.md) |
| $WIF flywheel (live balanceOf read + 50% holder discount) | Written, tested with mocked RPC; live read attempted, RPC timed out — discount activates when the RPC answers |
| Contracts (`GateAudit.sol`, `PolicyRegistry.sol`) | Written, **NOT compiled, NOT deployed** (no solc/Foundry in sandbox) |
| Front-end (Flat Globe: Interactive 3D + Magnetic hover) + local demo server | Written, smoke-tested locally (`/` 200, `/api/gate` ALLOW + BLOCK verified) |
| GitHub repo | **Created + pushed 10 Nov ~20:00 IST** — [MSAbhishek22/gateflat](https://github.com/MSAbhishek22/gateflat), head `3960c9055535` (33 files, read back live) |
| Vercel deploy | Not attempted |
| Demo video | Not recorded |
| Submission | Not submitted — deadline 12 Nov 23:00 IST |

**Honest summary:** the gate runs for real on your machine today, against the live Robinhood
Chain RPC when it answers. No real transaction has ever been sent — that needs the team lead's
own wallet, and the user's MetaMask address is not on file (see STATUS.md). The onchain half
is designed, written, and waiting for a deploy + a wallet.

## Run it locally

```bash
python3 -m unittest discover -s tests          # 108 tests
python3 app/server.py                           # http://127.0.0.1:8000
python3 app/server.py --allow 0x1111...         # demo with an allowlisted dest
```

## Layout

- `CONCEPT.md` — what it is, who pays, why it wins
- `RESEARCH.md` — verified vs unverified, with sources + dates
- `DESIGN.md` — the precise off-chain / onchain split
- `PLAN.md` — 2-day build plan + deployment runbook (deadline 12 Nov)
- `SUBMISSION_DRAFT.md` — what the form asks, what's still unknown
- `STATUS.md` — the honest ledger (what's real, what's scaffold)
- `design/` — design constitution + registry (Flat Globe)
- `app/` — scanner + policy + receipts (REUSED, labelled) · robinhood + wif + credits + gate + service + server + front-end (NEW)
- `contracts/` — GateAudit + PolicyRegistry (written, uncompiled)
- `tests/` — 108 tests (24 ported, 84 new)

## Reuse, labelled honestly

- `app/scanner.py`, `app/receipts.py` — ported verbatim from
  hermes-secret-gate (42/42 tests in its home repo, verified 9 Nov 2026).
- `app/policy.py` — ported verbatim from CageCheck (10/10 in its home repo).
- `app/tapeout.py` — the TapeOut Gate integration layer, carried over in
  the ported folder but NOT used by the GateFlat service (kept for
  reference; the live path is `robinhood.py` + `wif.py`).
- Everything Robinhood/$WIF-facing is NEW: chain constants + live probe,
  $WIF balanceOf read + holder discount, USDG demo ledger, gate
  orchestration, service, front-end, submission narrative.
- The event rules allow porting / existing work (rule 6) — the
  new-development list is in DESIGN.md §7.

## Rules that bind this project

Free-only, no card, no secrets in the repo, no invented addresses or
numbers, no claim of a deploy until an explorer link exists, no claim of
a transaction until a hash exists. The ABHI_22 quality rulebook applies:
this build is IN_PROGRESS, not COMPLETE — it lacks live HTTPS, a
live-recorded demo video, and the remaining gates.
