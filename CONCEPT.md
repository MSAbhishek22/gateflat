# CONCEPT — GateFlat

## The problem (real, specific)

Onchain agents draft contract calls — `to`, `value`, `data` — and send
them. The draft is where secrets leak: an agent that has seen a deploy
key, a wallet seed phrase in a config dump, or an API token in a log
will happily paste it into a memo field, a calldata argument, or a
"helper script" it writes to finish the job. One leaked key in one
transaction is public forever. Existing secret scanners live in editors
and CI; nothing stands between an *agent's draft* and the *chain*.

Robinhood Chain makes this urgent in a new way: it is a fresh L2 where
agents are invited to build and transact, and its token $WIF is the
community's coordination layer. An agent that can draft a call but
cannot prove the call is clean is a liability to every wallet it
touches.

## The product

GateFlat is a fail-closed gate that every agent-drafted call crosses
before it is dispatched toward a Robinhood Chain contract:

1. **Canonicalise + hash.** The draft becomes one deterministic JSON
   string; only its SHA-256 hash ever goes onchain — never the payload
   content, never a secret.
2. **USDG credit check.** One run costs 0.01 USDG of demo credit (0.005
   for $WIF holders). An account that cannot afford a run is HELD before
   any scan runs — no work is done for free, no secret is ever scanned
   on credit.
3. **Secret scan.** The hermes-secret-gate scanner reads the canonical
   text. LEAKED blocks; REVIEW holds.
4. **Policy scan.** If the draft carries agent-written code, the
   CageCheck policy engine reads it. BLOCKED blocks; HELD holds.
5. **Destination check.** Only an allowlisted destination allows; a
   blocklisted one blocks; an unknown one holds.
6. **Receipt + prepared record.** Every decision leaves a masked
   receipt (a receipt never carries secret material) and a prepared
   `GateAudit.recordDecision` call — payload hash, verdict, rules hash,
   receipt id — tagged with the Robinhood Chain it targets.

## The $WIF flywheel (rule 7)

Holding $WIF makes the gate cheaper: a live `balanceOf` read on
Robinhood Chain finds a positive $WIF balance, and the run costs half
price (0.005 USDG). Every gate run rewards holding $WIF, and every
$WIF holder gets a cheaper gate — use drives holding, holding drives
use. The read is fail-soft: a failed probe means "unknown", never a
fake holder status.

## Who pays, and why it keeps working

- **Agents and agent frameworks** pay per run in USDG (the chain's
  native stablecoin) because a leaked key costs infinitely more than
  a cent. The fee is the business model: the gate is a toll booth
  between drafting and dispatching.
- **$WIF holders** pay half, which gives the token a concrete utility
  beyond voting: cheaper safety.
- **Teams on Robinhood Chain** keep using it because the receipt is
  the audit trail — every dispatched call has a tamper-evident log
  entry they can show a user, an auditor, or a judge.

## Why it wins here

- It is native to this event: Robinhood Chain RPC, USDG credits, $WIF
  flywheel, and a prepared onchain record — every rule (3, 5, 7) is
  answered by a named feature, not a slide.
- It is honest about its limits: no real transaction is claimed until
  a hash exists, the contracts are labelled not-deployed, the $WIF
  token address is labelled unverified, and the demo ledger is labelled
  demo. Judges can verify every claim in the repo in minutes.
- It is a port with substantial new development (rule 6 allows it):
  the scanner/policy/receipt cores are reused and labelled; the entire
  Robinhood/$WIF/credits/service/front-end layer is new, written for
  this event in two days.
