# DESIGN CONSTITUTION — GateFlat

Status: describes the **Flat Globe UI** in `app/index.html`
(10 Nov 2026). Where the built UI differs from this file later, the
built UI wins and the difference must be stated here.

## 0. Style pick (permanent user rule, 9 Nov)

**Interactive 3D / Spatial Web ("Flat Globe") — chosen. Cinematic /
Film Noir — rejected for this project, and why:**

Film Noir was the TapeOut Gate style (a night desk for a secret-leak
guard). GateFlat is a different story: a flat world, one chain, one
token at its core. The globe — a spinning flat-earth disc with a
glowing $WIF core — says "world is flat" in one image, and the green
is Robinhood's green. Noir would have hidden the token; the globe
puts it at the centre.

## 1. The metaphor

A flat globe, spinning slowly, with the $WIF core pulsing at its
heart. Around it: the gate console (the desk where a call is judged),
the flywheel panel (the token that makes the gate cheaper), the
credits panel (the toll), and the receipts (the paper trail). One
screen, no navigation — a judge sees the whole product in 10 seconds.

## 2. Palette

- Night `#07090c`, panel `#0e1218`, panel-2 `#121823`, line `#1e2635`
- Ink `#e8eef7`, muted `#93a1b5`
- $WIF green `#00d084` (primary action + ALLOW), green-dim `#0a2e22`
- Hold amber `#ffb454`, block red `#ff5d6c`, gold accent `#f5c542` (rare)

## 3. Type

System UI for prose; ui-monospace for addresses, hashes, JSON, and
all numbers the user must trust (balances, block numbers, receipts).

## 4. Motion (performance rules are non-negotiable)

- Animate **transform + opacity only** — never width/height/top/left.
- Two techniques, mixed: 3D tilt/rotation (the globe's slow
  rotateY spin + pulsing core) and magnetic hover (buttons lift and
  scale 1.02 on hover, settle on active).
- One slow ambient animation (36s globe spin); verdict cards rise
  once (0.35s). Nothing else moves continuously.
- `prefers-reduced-motion` disables the spin, pulse, and rise. A
  visible Low-motion toggle does the same on demand.
- No particles, no multiple 3D canvases, no external fonts or images.

## 5. Honesty in the chrome

- The header chips always show the live chain state (live block
  number, or "unreachable right now"), the network (4663), the
  contract state ("not deployed"), and the ledger state ("demo USDG").
- The footer states the honest limits in plain words: no transaction
  is ever sent from the page, the $WIF token address is unverified,
  no key or seed phrase is ever asked for.
- Verdicts are colour + word, never colour alone (ALLOW/HOLD/BLOCK
  badges carry the word).
