# Football Predictor — Frontend Redesign: Matchday Broadcast

**Date:** 2026-08-10
**Status:** Approved (design phase) — pending user spec review
**Approach:** Full rebuild of the React 19 + Vite + Tailwind frontend around a stadium-broadcast visual concept, medium animation energy, using `motion` (framer-motion's new package) + CSS.

---

## 1. Visual Identity & Palette

Move off the current flat purple into a **stadium-night** system.

### Color tokens (`:root` in `index.css`)

| Token | Value | Use |
|---|---|---|
| `--pitch-black` | `#05070F` | App background |
| `--pitch-deep` | `#0A0E1A` | Card body (opaque) |
| `--pitch-edge` | `#1A2138` | Dividers / borders |
| `--turf` | `#0E3B2E` | Singular ambient tint (background breath, bottom-right radial) |
| `--flood` | `#7DD3FC` | Floodlight accent (cool light, sweeps + active state) |
| `--cream` | `#F4E9D8` | Numerical typography (scorelines, percentages, gameweek) |
| `--mute` | `#8B95B0` | Secondary text / labels |
| `--win` | `#22C55E` | Probability: home / win outcome |
| `--draw` | `#F59E0B` | Probability: draw outcome |
| `--loss` | `#EF4444` | Probability: away / loss outcome |

Team-color accents are **dynamic per match**: each `MatchCard` derives a home/away color pair from the existing `teamColors` map (already in `MatchCard.tsx`) and uses it for the card's left/right edge glow and the active probability segment. This is what makes each match visually distinct without per-match theme plumbing.

### Typography

Two roles, both loaded via Google Fonts (already partially wired):

- **Inter** — body text, labels, nav, metadata. Already in `index.html`, keep.
- **JetBrains Mono** — **all numerals**: scorelines, percentages, gameweek numerals, kickoff times. Mono face gives the broadcast-readout character. Add to `index.html` `<link>`.

### Surfaces

Replace `glass-card` translucency with **opaque** `--pitch-deep` cards + 1px `--pitch-edge` top border + single hard inner highlight (`inset 0 1px 0 rgba(255,255,255,0.04)`). Cleaner "broadcast panel" than frosted glass. Keep `backdrop-blur` only on the sticky header (so content scrolls behind it).

### Ambient (CSS only, fixed-position)

1. **Background breath** — two fixed radial gradients (`--flood` top-left, `--turf` bottom-right) with `@keyframes opacity 0.10 ↔ 0.18` over 8s, out of phase. `will-change: opacity`.
2. **Floodlight sweep** (on masthead `::before`) — a wide thin linear-gradient translating `translateX(-100% → 100%)` every 6s, 8s ease-in-out, opacity 0 → 0.35 → 0.

No canvas, no particles. Both statically positioned in `index.css`.

---

## 2. Layout & Component Architecture

### App shell
- Sticky `Header` — opaque `--pitch-black` with `backdrop-blur`, a `--flood` underline that subtly slides horizontally (ambient). Logo rebuilt as a mono "FP" lockup with a floodlight flare behind it.
- `<main>` stays single-column; max-width widens from `900px` → `960px` to give scoreboard cards room. Centered rail.

### Hero → Matchday Masthead
Replaces the existing `<div className="pl-hero">`. Taller (~200px) panel:
- Eyebrow: uppercase `MATCHDAY` (`--mute`, mono)
- Big gameweek numeral in mono (`MD 27`), the "27" count-up animates on mount and on gameweek change
- Subtitle: `Premier League • 2026/27`
- Ambient floodlight sweep (`::before`, described above)

### Gameweek Nav (fixture reel)
Rebuilds `.pl-gw-nav`. Instead of bare arrows + label:
- `‹` / `›` chevrons (`lucide-react`, already a dep) with hover floodlight glow
- Center: gameweek label + match count, flanked by **mini fixture pills** (3 per side) showing neighboring weeks' team-color dots so neighbors are glanceable. These derive from `matches` already loaded by `App.tsx` (every match for every gameweek is in client state — `getAllMatches` returns all of them; the pills just filter and take the first team-color from each neighbor week's first match). No extra API calls.
- On week change: the entire `MatchList` exits slide-left + fade, new enters slide-right + stagger via `AnimatePresence mode="wait"`

### MatchList
Keeps the sensible date-grouped structure. Changes:
- Date headers become a **broadcast slate** row: mono date + thin `--pitch-edge` rule that grows 0 → full width when group enters view (`whileInView`, once) using `Slate` component
- Each `MatchCard` animates with `staggerChildren: 0.05` from the parent group

### MatchCard (the scoreboard) — centerpiece
Wide horizontal panel, min-height ~140px:

```
┌──────────────────────────────────────────────────────────┐
│  [badge] HOME          [scoreline]      AWAY [badge]      │
│   MUN          KO 15:00   2–1           LIV               │
│  ────────────────────────────────────────────────────      │
│  PREDICTED   47% ████████░░░░░  26% ░░  27% ░░  → MUN     │
└──────────────────────────────────────────────────────────┘
```

- **Top row:** badge + short name (left/right), center stack with **count-up scoreline** (mono `--cream`, track-2px outline behind for contrast) + kickoff time chip
- **Divider rule** (animated width on mount)
- **Bottom row:** `PredictionBar` rebuilt as the `Meter` tri-segment + predicted winner ribbon that slides from right

### TeamBadge
Structurally unchanged. Reskin only: square corners (`--radius-sm`), `--pitch-edge` border, no fill. Image / error fallback logic unchanged.

### Component inventory

| Component | Action |
|---|---|
| `Header.tsx` | Rebuild (surface + logo) |
| `MatchList.tsx` | Rebuild (motion wrapper, stagger, `Slate`) |
| `MatchCard.tsx` | Rebuild (scoreboard layout + tilt) |
| `PredictionBar.tsx` | Rebuild (wire in `Meter`, drop stacked row markup) |
| `TeamBadge.tsx` | Reskin only |
| `Loader.tsx` | Rebuild (broadcast scan loader) |
| `ui/spotlight-card.tsx` (`GlowCard`) | **Delete** — replaced with motion-driven hover tilt in `MatchCard` |
| `ui/Meter.tsx` | NEW — tri-segment meter, used by `PredictionBar` |
| `ui/CountUp.tsx` | NEW — animated numerals on mount |
| `ui/Slate.tsx` | NEW — reusable broadcast strip (date headers, footer) |
| `lib/motion.ts` | NEW — shared variants/bindings |
| `App.tsx` | Rebuild render tree, add `AnimatePresence` on `MatchList` |

---

## 3. Motion System

Shared presets live in `frontend/src/lib/motion.ts`:

```ts
spring: { type: 'spring', stiffness: 220, damping: 26, mass: 0.9 }
eased:  { duration: 0.28, ease: [0.22, 1, 0.36, 1] }  // "out-expo-ish"
fast:   { duration: 0.16, ease: 'easeOut' }
```

### Entrance choreography

| Element | Variant | Implementation |
|---|---|---|
| Date slate header | slide-down 12px + fade, rule grows 0→100% | `whileInView` once, no stagger |
| MatchCard (each) | fade + slide-up 16px, 50ms stagger within group | parent variant `staggerChildren: 0.05` |
| Scoreline numerals | count-up 0 → target over 0.6s eased | `CountUp` component; `useReducedMotion` → instant |
| Probability meter segments | width 0 → target via spring | meter drives `scaleX` (transform-origin: left) so re-renders don't re-trigger |
| Predicted winner ribbon | slide-in from right, delay 0.5s after card enters | combined with same parent variant |
| Masthead "MD 27" | big count-up + `--flood` flare opacity breath | mount variant + CSS keyframe ambient |

### Matchweek transitions (the "fixture reel" feel)

`App.tsx` wraps `<MatchList>` in `<AnimatePresence mode="wait">`, keyed on `selectedGameweek`:
- exit: slide-left 24px + fade-out 0.16s
- enter: slide-right 24px + fade-in 0.22s (inner card stagger follows)

### Hover (per MatchCard)

- **3D tilt:** `rotateX/rotateY` driven by pointer position, capped to ±2°, `transformPerspective: 800`, `transformStyle: 'preserve-3d'`. Light `spring` so it settles back.
- **Team-color edge glow:** left/right inner box-shadow intensifies (CSS transition 200ms).
- **Predicted-winner segment sheen sweep:** CSS, 400ms.
- All hover effects disabled on touch devices (coarse-pointer check) and under reduced-motion.

### Reduced-motion gate

Top-level gate in `App.tsx`:

```ts
const reduce = useReducedMotion();
const entrance = reduce ? { initial: false } : { initial: 'hidden', animate: 'show' };
```

When true: disable count-up (render final), disable tilt, disable floodlight sweep (set static), keep only instant fade-ins. Tested against CSS `@media (prefers-reduced-motion: reduce)`.

### What we deliberately don't animate

- Individual probability bar widths after mount (only initial fill) — avoids constant motion on re-render.
- Text content updates (no shimmer on data reload — refresh shows instant swap).
- Scrolling itself (no scroll-driven slide-ins beyond date slates — would fight reading flow).

---

## 4. Signature Components

### `ui/Meter.tsx` — tri-segment probability meter

Replaces three stacked `.prob-row` rows with a single horizontal broadcast readout.

- One container, 8px tall, `--pitch-edge` track, `--radius-full`
- Three child segments laid out left → right (home, draw, away). Width = percentage, but **segment widths animate from 0 → target on mount** via `scaleX(0 → 1)` with `transformOrigin: left` (Section 3 spring). Using `scaleX` instead of `width` prevents re-render re-trigger.
- Each segment's color: dynamic team-color pair (home/away from `getTeamColor`); draw uses `--draw`. Predicted-winner segment gains a brighter overlay + subtle inner sheen sweep on hover (CSS).
- Active segment label climbs ~2px and gains `--flood` color on its label.
- Typography row above bar: `HOME 47% · DRAW 26% · AWAY 27%` — mono, `--mute`, active pair in `--cream`.
- Predicted winner **ribbon** (in `MatchCard`, right of scoreline, not inside meter): `<span className="ribbon">→ MUN WIN</span>` — pill shape, team-colored fill at 12% opacity + team-colored text + 1px team-color border. Slides from right with delay after card entrance. For draws: `→ DRAW` with neutral `--draw` styling.

`PredictionBar.tsx` still owns layout + data shaping so `MatchCard` usage stays one-line.

### `ui/CountUp.tsx` — animated numerals (~25 lines)

Props: `value: number`, `duration?: number = 0.6`, `format?: (n: number) => string`. Renders a `<motion.span>` whose text content is bound to a `MotionValue<string>`. The motion value is derived from a numeric `useMotionValue(0)` updated via `useTransform(disp, v => format ? format(v) : String(Math.round(v)))`, then `animate(disp, value, { duration, ease: [0.22,1,0.36,1] })` runs on mount (and when `value` changes).

```tsx
function CountUp({ value, duration = 0.6, format }: CountUpProps) {
  const reduce = useReducedMotion();
  const disp = useMotionValue(0);
  const text = useTransform(disp, v => (format ? format(v) : String(Math.round(v))));
  useEffect(() => {
    if (reduce) { disp.set(value); return; }
    const controls = animate(disp, value, { duration, ease: [0.22, 1, 0.36, 1] });
    return () => controls.stop();
  }, [value, reduce]);
  return <motion.span aria-hidden="true">{text}</motion.span>;
}
```

(The `motion/react` package supports rendering a `MotionValue<string>` as the child of a `motion.span` — this is the idiomatic pattern.)

Used for:
- Masthead gameweek numeral
- Each scoreline digit separately (60ms offset between digits, "–" separator static)
- Optional percentage numerals in meter labels (toggleable)

`useReducedMotion` short-circuits to instant. `format` prop pads percentages ("047%") or not, and handles the "–" separator outside CountUp.

### `ui/Slate.tsx` — reusable broadcast strip

Three slots (`leading`, `label`, `trailing`). Used for:
- Date group headers (label = "Saturday 14 March 2026", trailing = match count pill)
- Footer row (label = "Premier League 2026/27", trailing = "AI Predictions")
- Optional top-of-list "MATCHDAY MD 27 • 10 FIXTURES" strip

Visual: opaque, `--pitch-edge` divider underneath (animated width 0 → 100% on entrance), label in mono uppercase `--mute`, trailing in smaller mono `--mute` pill. Hover state optional.

### `Loader.tsx` — broadcast scan loader

Replaces the bare spinner. A wide thin `Meter`-style track with a single `--flood` segment sweeping left → right infinitely (CSS `@keyframes` 1.2s linear, `transform: translateX`). Underneath: mono label cycling through `FETCHING FIXTURES`, `LOADING PREDICTIONS`, `COMPILING MODEL` via a component interval. Clean, on-theme. Goes static under reduced-motion (track visible, label set to `LOADING…`).

---

## 5. Accessibility (cross-cutting)

- All mono numerals get a screen-reader-friendly `aria-label` with the literal value ("Matchday 27"); the visual count-up is `aria-hidden`. Screen-reader users never wait for an animation.
- The Meter bar has `role="img"` + `aria-label` summarizing (`47% home, 26% draw, 27% away — predicted home win`).
- Hover tilt gated behind coarse-pointer check so touch users never see a snapped/stuck tilt.
- Color (`--win/--draw/--loss` and team accents) **always paired with text labels** — never color-only signal (WCAG AA).

---

## 6. Build, Dependencies & Files

### Dependencies — one add

```diff
+ "motion": "^12.0.0"
```
`motion` is the modern successor to `framer-motion` — same authors, `motion/react` import path, React 19 compatible. `lucide-react`, `clsx`, `tailwind-merge` already present. No GSAP, no animation utility libs.

### Tailwind config (`tailwind.config.js`)

Currently unextended default. Add minimally:
- `fontFamily.mono`: `['JetBrains Mono', 'monospace']`
- `fontFamily.sans`: `['Inter', ...systemFallbacks]`
- `colors`: Section 1 palette tokens → enables `bg-pitch-deep`, `text-cream`, `border-pitch-edge`, etc.
- Bulk of styling stays in `App.css`/`index.css` (existing pattern); Tailwind is a complement, not a rewrite to utility-first.

### Fonts (`index.html`)

Pre-load JetBrains Mono alongside Inter:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300..800&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
```
Preconnect already present.

### Files touched / created

| File | Action | Approx lines |
|---|---|---|
| `frontend/src/index.css` | Rebuild palette, surfaces, ambient keyframes | ~200 |
| `frontend/src/App.css` | Rebuild layout classes (header, hero→masthead, gw-nav, card, meter) | ~450 |
| `frontend/src/App.tsx` | Rebuild tree, `AnimatePresence` on MatchList | ~140 |
| `frontend/src/components/Header.tsx` | Reskin | ~30 |
| `frontend/src/components/MatchList.tsx` | Wrap in motion + stagger, use `Slate` | ~70 |
| `frontend/src/components/MatchCard.tsx` | Rebuild scoreboard layout, tilt | ~110 |
| `frontend/src/components/PredictionBar.tsx` | Wire in `Meter`, drop stacked row markup | ~50 |
| `frontend/src/components/TeamBadge.tsx` | Reskin only (square, edge border) | ~same |
| `frontend/src/components/Loader.tsx` | Broadcast scan loader | ~30 |
| `frontend/src/lib/motion.ts` | NEW: shared variants/bindings | ~40 |
| `frontend/src/components/ui/Meter.tsx` | NEW | ~70 |
| `frontend/src/components/ui/CountUp.tsx` | NEW | ~35 |
| `frontend/src/components/ui/Slate.tsx` | NEW | ~50 |
| `frontend/src/components/ui/spotlight-card.tsx` | Delete | — |
| `frontend/index.html` | Add JetBrains Mono link | +1 line |
| `frontend/tailwind.config.js` | Extend fonts/colors | ~30 |

Round number: ~1300 lines touched/created, ~3 files deleted (one ~185-line component). Single-PR surface.

---

## 7. Edge & State Behavior

| State | Behavior |
|---|---|
| **API offline** | `error-state` slate: `--loss` edge, error pill, "RETRY" button (`window.location.reload()`). Animated `Slate` entrance. |
| **No matches for gameweek** | Empty `Slate` + a small inline empty-state panel (`MatchList`'s existing empty branch, re-styled to a `--pitch-deep` card with muted mono message "NO FIXTURES SCHEDULED"). Same motion profile as a card so empty state feels intentional, not missing. |
| **Initial load** | `Loader` (broadcast scan). Masthead renders immediately with `MD 00` placeholder that becomes `MD 27` only after data resolves — no jarring count from 0 during fetch latency. |
| **Coarse pointers (touch)** | Tilt disabled; hover edge-glow replaced by always-on subtle edge tint; no shimmer sweep. Everything else remains (motion is mount-driven, not pendulum). |
| **Reduced motion** | All intermittent motion halts (floodlight sweep, background breath, count-up). Card entrances become instant fades. App stays fully usable; identity preserved via color/typography. |
| **Count-up with nulls/zeros** | `0` and `undefined` render as literal `–` (not animated). Predicted score can be null for some matches — graceful `Kick Off` placeholder (same as existing behavior). |
| **Re-renders** | Once a card mounts, variants don't re-trigger (we use `initial`/`animate`, not `animate` on a re-render cycle). `Meter` segments use `scaleX()` from a motion value bound at mount — re-renders won't re-animate width. |
| **Badges 404** | TeamBadge fallback unchanged (initials pill), styled to match new `--pitch-edge` surface. |
| **Partial fixture data** | Degrade to existing "Kick Off" + "PREDICTED — unavailable" states, re-styled with new palette. |

---

## 8. Verification Plan (definition of done)

1. `frontend/package.json` installs cleanly (`npm install`).
2. `npm run lint` passes (eslint is configured; no `any` in new components beyond existing usage patterns in `MatchCard`).
3. `npm run build` passes Vite production build with no type errors.
4. Run dev server (`npm run dev`); smoke-test matchweek navigation (prev/next); confirm card stagger and meter fill work.
5. Manually toggle `prefers-reduced-motion: reduce` in DevTools; confirm: count-up instant, tilt absent, sweep absent, app usable.
6. Test touch-pointer simulation in DevTools (coarse pointer); confirm no tilt is triggered.
7. Stop the Python backend; confirm error slate renders with retry affordance and entrance animation.

---

## 9. Out of Scope (deliberately)

- New features (single-match predict UI, results view, etc.)
- Backend changes
- Routing (the app has one route)
- Tests — the existing repo has no frontend test setup; adding one is a separate decision, not introduced in this rebuild.

---

## 10. Open Questions / Assumptions

None remaining from the user. The design is internally consistent, scoped for medium-energy motion budget, and grounded in the existing `MatchCard.tsx` team-color map and `Match`/`Prediction` data shapes (`frontend/src/types.ts`). Assumption: the backend API contract (`getAllMatches`, `checkHealth` in `frontend/src/api/matches.ts`) is stable and unchanged by this redesign.
