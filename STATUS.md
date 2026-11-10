# STATUS — the honest ledger

Updated 10 Nov 2026 ~19:50 IST. This file is the only place that may claim
a state; README/CONCEPT/DESIGN defer to it.

## What is REAL (verified in this sandbox today)

- Research: official World Is Flat pages read in full (home, /build,
  /build/rules, /build/terms) — 2026 edition, deadline, solo, free,
  $10,000 USDG winner-take-all, judging + vote flow. See RESEARCH.md.
- Robinhood Chain facts: mainnet 4663, testnet 46630, RPCs, explorers —
  verified across Robinhood docs, QuickNode, Tangem, Triport, viem.
  Live probe from this sandbox 10 Nov ~19:25 IST: mainnet eth_chainId
  → 0x1237, eth_blockNumber 0x69c8efb, testnet eth_chainId → 0xb626.
  Chain contact is REAL.
- Gate core: scanner + policy + receipts ported from hermes-secret-gate
  and CageCheck — re-run and passing here.
- New integration layer (`app/robinhood.py`, `app/wif.py`,
  `app/credits.py`, `app/gate.py`, `app/service.py`) + local demo server
  + Flat Globe front-end — written and tested.
- **Tests: 112/112 PASS** — `python3 -m unittest discover -s tests`,
  Python 3.12, Linux sandbox, ~0.6s.
  Breakdown: scanner 18 (ported) + policy 6 (ported) + robinhood 36
  (new) + credits 10 (new) + gate 19 (adapted) + service 12 (new) +
  wif 11 (new).
- Local smoke test 10 Nov ~19:50 IST: `/` 200 (17,677 B Flat Globe UI),
  `/api/gate` ALLOW on the demo contract (balance 10.00 → 9.99 USDG),
  `/api/gate` BLOCK on a leaked GitHub token (secret absent from the
  receipt), `/api/wif` bad address → 400, `/api/credits` consistent
  across two runs (9.98 USDG).
- **Vercel deploy LIVE 10 Nov ~19:55 IST: https://gateflat.vercel.app/**
  (free Hobby; deployment dpl_5TZPUGc7Ro2YuvnCgWCKJKV3fSPz; verified
  in the browser: homepage loads, `/api/health` ok, `/api/gate`
  ALLOW live with receipt HSG-20261110-142525-0001, 9.99 USDG left).
- **RPC 403 on Vercel (found 10 Nov 19:55 IST):** the live
  `/api/chain` returns reachable:false, "HTTP Error 403: Forbidden"
  — the official Robinhood RPC rejects Vercel's servers. The site
  header honestly shows "Chain: unreachable right now". **Fix
  shipped same evening:** `rpc_call` fallback — official RPC first,
  then public no-key endpoints (publicnode, drpc, blockmachine);
  chainId is checked on every probe, so a fallback answering for a
  different chain is rejected. **Not yet verified live** — the
  sandbox cannot reach any RPC at all right now (all endpoints time
  out from here), so the live /api/chain after the redeploy is the
  real test.
- GitHub repo: **created + pushed 10 Nov ~20:00 IST** —
  https://github.com/MSAbhishek22/gateflat, head
  `3960c905553575f479103a7d27c2fca33e53f940` (33 files; provider
  "Initial commit" underneath, as expected — our README replaced
  the generated one). Read back live: README.md on main is the
  GateFlat README. Sync record saved.

## What is SCAFFOLD (written, not live)

- Contracts `GateAudit.sol` + `PolicyRegistry.sol`: written, **not
  compiled** (no solc/Foundry in sandbox), **not deployed**, no
  addresses exist.
- Front-end: built, serves locally only. No live URL.
- Demo video: not recorded. No video URL exists.
- Submission: not submitted. No confirmation exists.

## What is UNKNOWN / UNVERIFIED (do not claim)

- **$WIF token address** 0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B:
  secondary GitHub README only; NOT verified on official WIF pages or
  the Blockscout explorer. The holder discount is fail-soft: a wrong
  address yields "unknown", never a fake holder.
- **$WIF live read from this sandbox: TIMED OUT** 10 Nov ~19:45 IST —
  eth_call to the Robinhood mainnet RPC timed out at 5s and again at
  10s; a plain curl eth_chainId also timed out (8s). The same RPC
  answered fine at ~19:25 IST, so this is transient egress/RPC
  slowness, not proof the chain is down. The Vercel deployment must
  be checked live via its own /api/chain + /api/wif.
- **USDG token contract address on Robinhood Chain:** not verified;
  no address is referenced anywhere in the code. The USDG ledger is
  a local demo ledger — no real USDG ever moves.
- **User's MetaMask address:** user HAS MetaMask (created ~26 Jun
  2026) but does not remember the address; Gmail + MEMORY + workspace
  searched 10 Nov 19:22 IST — not on file anywhere. Needed as the
  prize payout address (Terms 8: paid to the team lead's wallet) and
  for any real transaction (rule 5). Recoverable only from the
  MetaMask app on his phone/laptop. User said 19:40 IST to proceed
  without it ("bina metamask ke kr").
- **Real transactions (rule 5):** none exist and none are possible
  without the user's wallet. The onchain record the gate prepares is
  a *prepared* call, not a sent one.
- Submission form URL + fields: behind Privy sign-in on
  worldisflat.fun/build — UNVERIFIED. India eligibility: not expressly
  confirmed (exclusions are sanctions-only; India was not on the
  checked prohibited list).

## Rulebook gate state

Per the ABHI_22 rulebook this project is **IN_PROGRESS**: research,
distinct design, working product (local), and QA (tests) are done;
live HTTPS deployment, GitHub/deploy commit match, demo video from
the live product, and final release evidence are all still open.
Do not call it COMPLETE until those pass.
