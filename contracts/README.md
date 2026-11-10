# Contracts — status

**Day 1 (9 Nov 2026): WRITTEN, NOT COMPILED, NOT DEPLOYED.**

No `solc` and no Foundry toolchain exist in the Day-1 sandbox, so no
compile was attempted and no compile claim is made. Week 2 compiles
these with Remix (browser, free, no install) against X Layer testnet
(chain ID 1952), then deploys and records the addresses + explorer
links in `STATUS.md` and `SUBMISSION_DRAFT.md`. Until then, every
address field in this repo is `TBD — not deployed`.

## GateAudit.sol

Append-only audit log. `recordDecision(bytes32 payloadHash, uint8
verdict, bytes32 rulesHash, string receiptId)` emits `GateDecision` and
stores the record. Only hashes/verdicts/receipt ids go onchain — never
payload content, never secrets. Verdicts: 0 = ALLOW, 1 = HOLD, 2 = BLOCK.
No owner, no upgrade path, no token, no fee logic. Anyone can log; the
`sender` field in the event makes the logger auditable.

## PolicyRegistry.sol

Allowlist / blocklist of destination contract addresses, with
`status(address)` returning 0 = UNKNOWN, 1 = ALLOW, 2 = BLOCK
(blocklist wins over allowlist). Single owner (the deployer) in v1 —
a pragmatic hackathon starting point, stated as a limit in DESIGN.md
§6, not a decentralisation claim. Multisig ownership is a v2 step.

## Design choices worth defending to a judge

- The contract stores the caller-supplied hash rather than recomputing
  it: no keccak-vs-sha256 mismatch between Python and Solidity, and
  the contract never sees payload bytes at all.
- The log is tamper-evident evidence, not a proof the scan ran. The
  receipt's replay string (re-run the scan, same verdict) is the proof,
  and it runs offchain where the deterministic scanner lives.
- No token, no payments, no per-call fee in v1: the revenue story in
  the submission is a per-team / per-deployment licence + hosted
  verifier, not a token (see CONCEPT.md).
