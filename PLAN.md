# PLAN — 2 days to the 12 Nov 2026 submission

Deadline: **Thu 12 Nov 2026 23:00 IST** (17:30 UTC — verified on the
official /build/rules page 10 Nov 2026).
Safe target: **submit by Wed 11 Nov 2026 20:00 IST**, leaving a buffer
for a form quirk or a re-record.

## Day 1 — Mon 10 Nov (done)

- [x] Research (official World Is Flat pages, Robinhood Chain docs) — RESEARCH.md
- [x] Port: scanner/policy/receipts verbatim; new robinhood.py + wif.py +
  credits.py; gate.py adapted; service.py + server + Vercel adapter
- [x] $WIF flywheel: live balanceOf read + 50% holder discount, fail-soft
- [x] Flat Globe front-end (Interactive 3D + Magnetic hover) + local smoke test
- [x] Tests: **108/108 PASS** (24 ported, 84 new)
- [x] Docs: README / CONCEPT / RESEARCH / DESIGN / PLAN / STATUS /
  SUBMISSION_DRAFT + design constitution + registry rewritten for GateFlat

## Day 2 — Tue 11 Nov (to do)

- [ ] Vercel deploy (free Hobby, no card) — verify live `/`, `/api/health`,
  `/api/chain` (does the Vercel egress reach the Robinhood RPC?),
  `/api/wif`, `/api/gate` ALLOW + BLOCK
- [ ] GitHub repo `gateflat` — create via signed-in browser, push via
  connector (user approval), record the snapshot head
- [ ] Demo video: screen-record the LIVE URL with ≥1 real action
  (ALLOW run + $WIF check), upload to YouTube as Public, verify it plays
- [ ] UKIS retry 09:00 IST (separate cron — do not let it slip)
- [ ] Submit on worldisflat.fun/build before 20:00 IST safe target —
  sign in via Privy (email code to msabhishekbdps@gmail.com per the
  sign-in rule); capture confirmation; record payout wallet status
  honestly (user's MetaMask address still not on file)

## If the wallet address arrives

- Paste it into the submission's payout field and into the demo video's
  $WIF check (a real holder read, if he holds $WIF).
- If he holds no $WIF, record that honestly — the flywheel still works
  for any holder; the demo uses the demo contract + a zero-balance read.

## Deployment runbook (Vercel)

1. `vercel.json` rewrites all routes to `/api/index` (already written).
2. Deploy from the repo (or `vercel --prod` via browser task — no card).
3. Verify live: `/` returns the Flat Globe UI; `/api/health` status ok;
   `/api/chain` reachable (or honestly unreachable with an error string);
   `/api/gate` ALLOW + BLOCK from the live URL.
4. If the Robinhood RPC is unreachable from Vercel too, the app still
   works (fail-soft) — record it in STATUS.md and in the submission
   text; do not fake a live chain read.

## Risks

- **Deadline is 2 days away.** No scope growth: no contract deploy
  attempt unless a free, no-card path exists and time remains after
  the video + submission are safe.
- **RPC flakiness.** The sandbox could not reach the RPC at ~19:45 IST
  after reaching it at ~19:25 IST. Vercel egress may differ — verify,
  don't assume.
- **Wallet.** No real transaction is possible without the user's
  MetaMask address. The submission must state this honestly (rule 5
  proof is repo + video + prepared records; real transactions pending
  wallet).
- **Form fields unknown.** The Privy sign-in hides the form; budget
  30 minutes at submission time for unknown fields.
