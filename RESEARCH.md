# RESEARCH — World Is Flat / Robinhood Chain / $WIF

Researched 10 Nov 2026. Every claim below is marked VERIFIED (read on the
source named) or UNVERIFIED (not yet established — do not build on it
until checked). Nothing here is copied from a secondary summary without
saying so.

## 1. The event — VERIFIED (official pages, browser read 10 Nov)

Sources: https://worldisflat.fun/ , https://worldisflat.fun/build ,
https://worldisflat.fun/build/rules , https://worldisflat.fun/build/terms
— full page text read 10 Nov 2026, recorded in
~/workspace/hackathons/x-hunt-2026-11-15/FINDINGS.md §5.

- **2026 edition.** Building since 21 Oct 2026. **Deadline Thu 12 Nov
  2026 17:30 UTC = 23:00 IST.**
- **Prize: $10,000 USDG, winner-take-all**, paid to the team lead's
  wallet within 7 days of the winner announcement (Terms 8).
- **Solo allowed** ("build alone or with a team of up to 4").
- **Free** — no $WIF holding required to enter.
- **Port / existing work allowed** (rule 6).
- **Judging:** judges pick top 10 (12–14 Nov); community vote with $WIF
  (14–16 Nov, votes burn $WIF); winner announced 16 Nov. 37 projects
  listed at check time.
- **Not affiliated with Robinhood Markets** — run by "world is flat".
- **India:** NOT expressly confirmed. Exclusions are sanctions-only
  and India was not on the checked prohibited list.

## 2. The rules that shape the build — VERIFIED (official /build/rules)

- **Rule 3:** the project "has to use $wif onchain on Robinhood Chain".
  → GateFlat reads $WIF live (balanceOf) and discounts holder runs.
- **Rule 4:** the project must stay live and working until the final
  closes. → The Vercel deployment must not be torn down before 16 Nov.
- **Rule 5:** proof = visible repo + demo video + **real transactions**.
  → The gate prepares a real `recordDecision` call; no transaction
  has been sent yet (needs the user's wallet — see §5).
- **Rule 7:** the project needs a **$WIF flywheel**. → Holder
  discount: holding $WIF halves the run price.
- **Submission route:** sign in on worldisflat.fun/build (email or X
  via Privy). Exact form fields behind sign-in UNVERIFIED.

## 3. Robinhood Chain — VERIFIED (multiple sources + live probe)

Sources: docs.robinhood.com/chain, robinhood.com support, QuickNode,
Tangem, Triport, viem chain definitions — consistent 10 Nov 2026.

- **Mainnet chain ID 4663 (0x1237)**, RPC
  https://rpc.mainnet.chain.robinhood.com, explorer
  https://robinhoodchain.blockscout.com, gas ETH, Arbitrum Nitro L2.
  Mainnet live 1 Jul 2026.
- **Testnet chain ID 46630 (0xb626)**, RPC
  https://rpc.testnet.chain.robinhood.com, explorer
  https://explorer.testnet.chain.robinhood.com. Testnet live 10 Feb 2026.
- **USDG is the Paxos USD stablecoin** and Robinhood Chain's native
  stablecoin (Robinhood docs). The USDG token contract address on
  Robinhood Chain is NOT verified — no address is stated anywhere in
  this project.
- **Live probe from this sandbox 10 Nov ~19:25 IST:** mainnet
  eth_chainId → 0x1237, eth_blockNumber 0x69c8efb (advancing), testnet
  eth_chainId → 0xb626. Chain contact is REAL.
- **Live probe 10 Nov ~19:45 IST: TIMED OUT.** eth_chainId and
  eth_call both timed out (5s, then 10s; plain curl eth_chainId timed
  out at 8s). The RPC answered 20 minutes earlier, so this is
  transient egress/RPC slowness, not proof the chain is down. The
  app is fail-soft (unreachable chain = "unreachable", never a crash),
  and the Vercel deployment must be checked live via its own
  /api/chain + /api/wif.

## 4. $WIF token — UNVERIFIED (secondary source only)

- **RobinWifHat 0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B** — from a
  secondary GitHub README (wif-desk) only. NOT verified on the
  official worldisflat.fun pages or on the Blockscout explorer.
- Decimals assumed 18 (ERC-20 default, unverified for this token).
  A wrong decimals value only mis-scales the displayed balance; the
  holder test (balance > 0) is unaffected.
- A wrong token address yields "unknown" (fail-soft), never a fake
  holder status.

## 5. What is still UNKNOWN (do not claim)

- User's MetaMask address: user HAS MetaMask (created ~26 Jun 2026)
  but does not remember the address; Gmail + MEMORY + workspace
  searched 10 Nov 19:22 IST — not on file. Needed for the prize
  payout address and any real transaction. Recoverable only from the
  MetaMask app on his phone/laptop. User said 19:40 IST to proceed
  without it.
- Submission form fields (behind Privy sign-in).
- India eligibility (not expressly confirmed — see §1).
- USDG token contract address (see §3).
- Whether the Vercel deployment can reach the Robinhood RPC (to be
  verified live after deploy).
