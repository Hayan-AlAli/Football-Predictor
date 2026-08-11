# Animated Background — Broadcast Dither Masthead + Floodlight Dust Motes

Date: 2026-08-11
Status: Approved (design)
Applies to: frontend (React + Vite + Tailwind + motion)

## Goal

Add an animated background to the Matchday Broadcast frontend:

1. **Dust motes** — page-wide ambient layer: tiny flood-blue particles drifting upward like dust in stadium floodlights.
2. **Dither wave** — a React Bits-style WebGL dithering wave filling the masthead band, evoking a broadcast-monitor/phosphor identity.

The dither wave is the masthead's ambient; dust motes are the page's ambient. Both must stay visually subordinate to content, cheap to render, and static under `prefers-reduced-motion`.

## 1. Dust motes (page-wide)

- New component `frontend/src/components/AmbientMotes.tsx`, mounted once at the top of `App.tsx`.
- Fixed full-viewport layer, `pointer-events: none`, `z-index: -1` (same layer as existing ambient gradients in `index.css`).
- Three depth layers (each: outer div does vertical drift, inner div does horizontal sway — two transforms cannot share one element):
  - **Far:** 1px dots, opacity 0.10, 60s upward loop, slowest sway
  - **Mid:** 1.5px dots, opacity 0.14, 45s loop
  - **Near:** 2px dots, opacity 0.18, 30s loop, fastest sway
- Dots are CSS-only: each layer is a repeating `radial-gradient` tile (`background-size` ~240px, 3–4 dot stops with varying alpha), on a layer 200vh tall so `translateY(0 → -100vh)` loops seamlessly.
- Dot color: `--flood` (sky blue `#7DD3FC`).
- Fade-in over ~2s on load (opacity keyframe).
- Reduced motion: static layer at ~0.12 opacity (matches existing pattern in `index.css`).
- Performance: 6 fixed elements, transform/opacity animations only, `will-change: transform` on the 3 outer layers.

## 2. Dither wave (masthead band)

- Copy the React Bits `Dither` component source (MIT, self-contained: canvas + requestAnimationFrame + fragment shader, zero dependencies) into `frontend/src/components/effects/Dither.tsx`. No npm dependency.
- Mount inside `Masthead.tsx` as an absolute `inset-0` layer behind the `MATCHDAY` / `MD xx` / kicker composition and the broadcast ticker, clipped to the masthead band.
- Tuning (props):
  - `baseColor` `#05070F` (pitch-black)
  - `waveColor` `[0.49, 0.83, 0.99]` (`--flood` `#7DD3FC`)
  - `pixelSize` 6, `colorNum` 4
  - `waveAmplitude` 0.25, `waveFrequency` 3, `waveSpeed` 0.03 (slower than default 0.05)
  - `enableMouseInteraction` false (masthead is non-interactive; no pointer-event fork)
- Reduced motion: derive `disableAnimation` from `useReducedMotion`; when true, render the first dithered frame statically.
- Cleanup: the dither **replaces** the masthead floodlight sweep (`::before` in `App.css`). Ticker remains above the dither.
- Performance: render loop bounded to the masthead band (fraction of viewport), canvas sized at `devicePixelRatio`, loop paused when `document.hidden`.

## 3. Files

- **New:** `frontend/src/components/AmbientMotes.tsx`, `frontend/src/components/effects/Dither.tsx`
- **Edit:** `frontend/src/App.tsx` (mote mount), `frontend/src/components/Masthead.tsx` (dither mount), `frontend/src/index.css` (mote layer styles in the Ambient Background section), `frontend/src/App.css` (masthead: remove sweep, add dither container)

## 4. Verification

- `npm run lint`, typecheck, `npm run build` in `frontend/`
- Visual check at http://localhost:5173 — motes visible but quiet; masthead shows the dithered flood-blue wave; cards unaffected
- Reduced-motion check — static dither frame, static motes
- Scroll stays smooth (no jank from the fixed layers)
