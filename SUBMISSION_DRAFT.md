# SUBMISSION DRAFT — World Is Flat Hackathon (Robinhood Chain)

Status: DRAFT, 10 Nov 2026. The form itself has not been seen yet —
its URL and field list are UNKNOWN (behind Privy sign-in on
worldisflat.fun/build — see RESEARCH.md §2). This draft holds
everything the official rules say the submission must prove, so
filling the form is mechanical once the link is captured. Nothing
below is submitted anywhere.

## What the official rules require

- **Visible repo** (rule 5) — https://github.com/MSAbhishek22/gateflat
  (public, head `3960c905553575f479103a7d27c2fca33e53f940`, 33 files,
  read back live 10 Nov ~20:00 IST).
- **Demo video** (rule 5) — screen recording of the LIVE URL with
  ≥1 real action (ALLOW run + $WIF balance check), YouTube Public.
- **Real transactions** (rule 5) — PENDING the user's wallet. The gate
  prepares a real `GateAudit.recordDecision` call; no transaction has
  been sent. State this honestly in the form; do not claim a hash
  that does not exist.
- **Uses $WIF onchain** (rule 3) — live `balanceOf` read on Robinhood
  Chain mainnet (eth_call, no signing) + holder discount.
- **$WIF flywheel** (rule 7) — holding $WIF halves the run price
  (0.005 vs 0.01 USDG); use rewards holding, holding rewards use.
- **Stays live until the final closes** (rule 4) — Vercel deployment
  must not be torn down before 16 Nov 2026.

## Project description (paste-ready)

**GateFlat — the $WIF gate on Robinhood Chain.** Before an agent's
drafted contract call reaches the chain, it crosses this gate: secrets
get blocked, unknown destinations get held, every decision leaves a
masked receipt and a prepared onchain record — and $WIF holders run
the gate at half price. The gate is a toll booth between drafting and
dispatching: agents pay per run in USDG (the chain's native
stablecoin), holders pay half, and every dispatched call carries a
tamper-evident audit entry. Built as a port of TapeOut Gate (its own
live OKX entry, untouched) with a fully new Robinhood/$WIF layer:
live chain probe, $WIF balanceOf read, USDG demo ledger, and a Flat
Globe front-end.

## Links (fill in as they land)

- Live URL: _TBD (Vercel deploy 11 Nov)_
- Repo: https://github.com/MSAbhishek22/gateflat (public, head `3960c9055535`)
- Demo video: _TBD (YouTube Public)_
- Contracts: GateAudit + PolicyRegistry — written, NOT deployed
  (no solc in sandbox; state this in the form)
- Payout wallet (team lead): _TBD — user's MetaMask address not on
  file; recoverable only from his MetaMask app_

## Honest disclosures for the form

- $WIF token address (0xE49A…0F9B) is from a secondary source and is
  labelled unverified; the holder check is fail-soft.
- The USDG ledger is a local demo ledger; no real USDG moves.
- No real transaction exists yet (wallet pending).
- The Robinhood RPC was reachable from the sandbox at 19:25 IST and
  timed out at 19:45 IST (transient); the Vercel deployment's own
  /api/chain reading is the live check.
