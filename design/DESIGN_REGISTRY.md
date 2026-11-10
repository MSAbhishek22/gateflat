# DESIGN REGISTRY — GateFlat

The registry of every visual decision, so the identity never repeats
and never drifts silently. Updated when the built UI changes.

## Identity

- **Style:** Interactive 3D / Spatial Web — "Flat Globe" (chosen 10 Nov
  2026; Cinematic / Film Noir explicitly rejected for this project —
  see DESIGN_CONSTITUTION.md §0).
- **Metaphor:** flat globe — spinning disc + glowing $WIF core; gate
  console + flywheel + credits + receipts around it.
- **Palette:** night `#07090c`, panel `#0e1218`, panel-2 `#121823`,
  line `#1e2635`, ink `#e8eef7`, muted `#93a1b5`, $WIF green `#00d084`,
  green-dim `#0a2e22`, hold amber `#ffb454`, block red `#ff5d6c`,
  gold `#f5c542` (rare accent).
- **Type:** system-ui prose; ui-monospace for addresses, hashes, JSON,
  balances, block numbers, receipts.

## Elements

- **Globe:** 148px disc, radial-gradient flat-earth shading, two
  latitude rings, pulsing core; `rotateY` spin 36s linear infinite;
  `perspective: 900px` wrapper.
- **Buttons:** pill radius, $WIF green primary, ghost secondary;
  hover lifts -2px + scale 1.02 with green shadow; active settles.
- **Cards:** 16px radius, 1px line border, 18px padding; two-column
  grid (gate console 1.15fr, side panels .85fr), single column under
  860px.
- **Verdict:** hidden until a run; rises once (translateY 8px → 0,
  0.35s); badge pill with the decision word; ALLOW green-dim,
  HOLD amber-dark, BLOCK red-dark.
- **Chips (header):** 12.5px pills; chain chip turns green with a live
  block number, amber when unreachable; contracts chip always amber
  ("not deployed") until a deploy exists.
- **Motion toggle:** fixed bottom-right pill; toggles `low-motion`
  on the body; `aria-pressed` reflects state.

## Decisions log

- 10 Nov 2026: Flat Globe chosen over Film Noir (constitution §0).
- 10 Nov 2026: magnetic hover kept to transform-only lift; no
  cursor-tracking JS (keeps the perf rules honest).
- 10 Nov 2026: no external fonts/images — the globe is pure CSS
  (radial gradients + borders), so the page has zero external
  dependencies.
