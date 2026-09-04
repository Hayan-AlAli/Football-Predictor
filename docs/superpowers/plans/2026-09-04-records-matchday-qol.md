# Matchday + Records QoL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The book opens on this week, records gains a folio index strip, and club columns print legible names with real crests.

**Architecture:** A pure, tested `currentGameweek()` picker drives the matchday default; records gets a sticky index strip with scroll-spy plus per-section tallies; both record groupings reuse the forecast legibility pattern. No endpoint changes.

**Tech Stack:** React 19 + Vite + TypeScript + Tailwind CSS, motion/react, vitest (new).

## Global Constraints

- Almanack world holds: hairlines, stamps, chips, Fragment Mono labels, square corners, ink/rubric/ledger palette only.
- API response shapes do not change; the frontend needs no new endpoints.
- Empty, offline, and error states keep their copy and behavior; only rows change.
- Reduced motion honored everywhere (smooth scroll + IntersectionObserver gated).
- TDD: failing test first for every behavior change; commit per task.

---

### Task 1: `currentGameweek()` picker + vitest setup

**Files:**
- Create: `frontend/src/lib/gameweek.ts`
- Create: `frontend/src/lib/gameweek.test.ts`
- Modify: `frontend/package.json`, `frontend/vite.config.ts`

**Interfaces:**
- Consumes: `Match { date: string; gameweek?: number }` from `../types`.
- Produces: `currentGameweek(gameweeks: number[], matches: Match[], today: string): number | null` — used by Task 2.

- [ ] **Step 1: Add vitest and a test script**

```bash
cd frontend
npm install -D vitest
```

In `frontend/package.json`, add to `scripts`:

```json
"test": "vitest run"
```

- [ ] **Step 2: Write the failing test**

```ts
import { describe, expect, it } from 'vitest';
import { currentGameweek } from './gameweek';
import type { Match } from '../types';

const mk = (date: string, gameweek: number): Match =>
  ({ id: `${date}`, date, gameweek, home_team: 'A', away_team: 'B' }) as Match;

describe('currentGameweek', () => {
  const matches = [mk('2026-08-22', 1), mk('2026-08-29', 2), mk('2026-09-05', 3)];

  it('picks the gameweek containing today', () => {
    expect(currentGameweek([1, 2, 3], matches, '2026-08-29')).toBe(2);
  });

  it('falls back to the nearest upcoming gameweek', () => {
    expect(currentGameweek([1, 2, 3], matches, '2026-08-25')).toBe(2);
  });

  it('falls back to the latest gameweek past the end', () => {
    expect(currentGameweek([1, 2, 3], matches, '2026-12-01')).toBe(3);
  });

  it('returns null for empty input', () => {
    expect(currentGameweek([], [], '2026-08-29')).toBeNull();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npm test -- src/lib/gameweek.test.ts` (from `frontend/`)
Expected: FAIL with "Cannot find module './gameweek'".

- [ ] **Step 4: Write minimal implementation**

```ts
import type { Match } from '../types';

/** Gameweek whose matches contain today; else nearest upcoming, else latest. */
export function currentGameweek(
  gameweeks: number[],
  matches: Match[],
  today: string,
): number | null {
  if (gameweeks.length === 0) return null;
  const byGw = new Map<number, string[]>();
  for (const m of matches) {
    if (m.gameweek == null) continue;
    const list = byGw.get(m.gameweek) ?? [];
    list.push(m.date);
    byGw.set(m.gameweek, list);
  }
  // Exact-date match first (match dates are single days; every date of a
  // multi-day gameweek is in the list, so this covers whole weeks).
  const containing = gameweeks.find((gw) =>
    (byGw.get(gw) ?? []).includes(today),
  );
  if (containing != null) return containing;
  const upcoming = gameweeks
    .map((gw) => ({
      gw,
      first: (byGw.get(gw) ?? []).slice().sort()[0],
    }))
    .filter((x) => x.first != null && x.first >= today)
    .sort((a, b) => (a.first as string).localeCompare(b.first as string));
  if (upcoming.length > 0) return upcoming[0].gw;
  return gameweeks[gameweeks.length - 1];
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- src/lib/gameweek.test.ts` (from `frontend/`)
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/gameweek.ts frontend/src/lib/gameweek.test.ts frontend/package.json frontend/package-lock.json
git commit -m "feat: currentGameweek picker with tests"
```

---

### Task 2: Matchday opens on this week + stamp

**Files:**
- Modify: `frontend/src/pages/MatchdayPage.tsx` (default selection + stamp)
- Modify: `frontend/src/components/RunningHead.tsx` (stamp passthrough)

**Interfaces:**
- Consumes: `currentGameweek` (Task 1), `useData()` matches/gameweeks, `useBook()` selection.
- Produces: nothing new (behavior change only).

- [ ] **Step 1: Write the failing test**

No new unit test (selection is hook state); verify manually in Step 4.
Instead assert the contract in code review: default selection equals
`currentGameweek(gameweeks, matches, today)` when `selected == null`.

- [ ] **Step 2: Change the default selection**

In `MatchdayPage.tsx`, replace:

```tsx
useEffect(() => {
  if (selected == null && gameweeks.length > 0) {
    setSelected(gameweeks[0]);
  }
}, [gameweeks, selected, setSelected]);
```

with:

```tsx
const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
const thisWeek = useMemo(
  () => currentGameweek(gameweeks, matches, today),
  [gameweeks, matches, today],
);

useEffect(() => {
  if (selected == null && thisWeek != null) {
    setSelected(thisWeek);
  }
}, [thisWeek, selected, setSelected]);
```

- [ ] **Step 3: Stamp the current folio**

Next to the gameweek numeral in the page-turn nav, render when
`selected === thisWeek`:

```tsx
{selected === thisWeek && thisWeek != null && (
  <span className="stamp" style={{ background: 'var(--rubric)' }}>
    This week
  </span>
)}
```

Pass `isCurrentWeek={selected === thisWeek}` into `RunningHead` and render
the same stamp there (small, beside the folio). Keep the prop optional so
other pages are unaffected.

- [ ] **Step 4: Verify**

Run: `npm test` (from `frontend/`) — Task 1 tests still green.
Run: `npx tsc --noEmit` — exit 0.
Manual: `npm run dev`, open `/` — this week's folio selected with the stamp;
turn pages — stamp follows only the current week.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/MatchdayPage.tsx frontend/src/components/RunningHead.tsx
git commit -m "feat: matchday opens on this week with stamp"
```

---

### Task 3: Records index strip + tallies + section ids

**Files:**
- Modify: `frontend/src/pages/RecordsPage.tsx`

**Interfaces:**
- Consumes: existing `grouped` memo (gameweek/date groups with lists).
- Produces: nothing new (behavior change only).

- [ ] **Step 1: Add stable section ids**

In the grouped-section render, set the section element's `id` to
`gw-${group.gw}` when `group.gw != null`, else `date-${group.date}`.
(Keep the existing `key` values as they are.)

- [ ] **Step 2: Add the index strip**

Directly under the page header, render a sticky ruled strip:

```tsx
<nav aria-label="Index of matchweeks" className="sticky top-0 z-10 -mx-4 border-y border-paper-line bg-paper px-4 py-2">
  <span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">Index</span>
  <span className="ml-3 inline-flex flex-wrap gap-x-3 gap-y-1">
    {grouped.map((group) => {
      const id = group.gw != null ? `gw-${group.gw}` : `date-${group.date}`;
      const label = group.gw != null ? `${group.gw}` : group.date;
      return (
        <a
          key={id}
          href={`#${id}`}
          data-index-link={id}
          className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-soft hover:text-rubric"
        >
          {label}
        </a>
      );
    })}
  </span>
</nav>
```

Clicking scrolls via the anchor natively. For reduced motion, add
`scroll-behavior: smooth` only under `@media (prefers-reduced-motion: no-preference)`
in the page's stylesheet scope (index.css utility layer, `.scroll-smooth-motion` class
applied on the nav's scroll container — do not set global smooth scrolling).

- [ ] **Step 3: Scroll-spy the active numeral**

Track the visible section with an `IntersectionObserver` (rootMargin `-40% 0px -55% 0px`)
over the section ids; store `activeId` in state; apply `text-rubric` instead of
`text-ink-soft` to the matching link. Disconnect on unmount. Skip observer setup
entirely when `useReducedMotion()` is true (no active switching — static list).

- [ ] **Step 4: Per-section decided tallies**

In each section header, right of the title, render:

```tsx
<span className="font-mono text-[0.625rem] uppercase tracking-widest text-ink-faint">
  {correct} correct · {incorrect} incorrect
</span>
```

computed from that group's list (CORRECT/INCORRECT counts; omit when both are zero).

- [ ] **Step 5: Verify**

Run: `npm test`, `npx tsc --noEmit` — green.
Manual: open `/records` — strip visible, links scroll to sections, active numeral
inks rubric while scrolling, tallies read correctly.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/RecordsPage.tsx frontend/src/index.css
git commit -m "feat: records index strip with scroll-spy and tallies"
```

---

### Task 4: Records legibility (names + crests)

**Files:**
- Modify: `frontend/src/pages/RecordsPage.tsx`

**Interfaces:**
- Consumes: `entry.match.home_team_info` / `away_team_info` (already in API shape), `TeamBadge`.
- Produces: nothing new.

- [ ] **Step 1: Full names with title fallback**

Replace both `teamShort(home)` / `teamShort(away)` call sites in the row
render with the full names:

```tsx
<span
  className="flex min-w-0 items-center gap-1.5 truncate font-sans text-sm font-bold uppercase tracking-caps text-ink"
  title={`${homeName} vs ${awayName}`}
>
```

where `homeName`/`awayName` resolve `m.home_team_info ?? m.home_team`
(the same expression already used for `home`/`away`) to a string name.
Remove the now-unused `teamShort` import if no other use remains in the file.

- [ ] **Step 2: Real crests at md**

Change both row `TeamBadge` usages from `size="sm"` to `size="md"` and pass
`info={m.home_team_info}` / `info={m.away_team_info}`. Keep the initials
fallback untouched (it renders automatically when `badge_url` is absent).

- [ ] **Step 3: Verify**

Run: `npm test`, `npx tsc --noEmit`, `npx eslint src/pages/RecordsPage.tsx` — green.
Manual: `/records` rows show full names + crests; long names truncate with
full text on hover.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/RecordsPage.tsx
git commit -m "feat: records full names and real crests"
```

---

### Task 5: Detector + final check

- [ ] **Step 1: Run the impeccable detector once over all touched UI**

Run: `node C:\Users\Hayan\.config\opencode\skills\impeccable\scripts/detect.mjs --json frontend/src/lib/gameweek.ts frontend/src/pages/MatchdayPage.tsx frontend/src/pages/RecordsPage.tsx frontend/src/components/RunningHead.tsx`
Expected: `[]`. Fix any finding in the owning task's file, no new tasks.

- [ ] **Step 2: Full frontend verification**

Run from `frontend/`: `npm test`, `npx tsc --noEmit`, `npx eslint .`
Expected: all green.
