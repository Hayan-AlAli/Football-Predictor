# Design: Matchday + Records QoL (folio furniture)

## Goal
Three quality-of-life improvements inside the Matchday Almanack world, no new
patterns: the book opens on this week, the records gain an index, and club
columns become legible.

## Decisions (user-approved)
- Approach A (in-world folio furniture) over utility chrome and URL-driven nav.
- Matchday defaults to this week with a stamp; manual page-turns override.
- Records nav is a sticky folio-numeral index strip (my choice, user-delegated).
- Legibility mirrors the forecast treatment both tables already approved.

## Section 1 — This week
- On load with no manual selection, the matchday opens on the gameweek whose
  match dates contain today. Fallback order: nearest upcoming gameweek, then
  latest available. A manual page-turn overrides freely afterward.
- The current folio carries a rubric "this week" stamp beside the numeral;
  the running head repeats the stamp while the current week is selected.
- Pure function `currentGameweek(gameweeks, matches, today)` in `lib/`
  so it is unit-testable with fixed dates.

## Section 2 — Index of matchweeks
- Records prints a sticky ruled strip under the header: mono folio numerals,
  one per section, in ascending order. Tapping a numeral smooth-scrolls to
  its section (respecting reduced motion); the numeral of the section
  nearest the viewport top inks rubric (IntersectionObserver).
- Each matchweek section header gains its decided tally
  ("3 correct · 2 incorrect") set small in ink-faint, right of the title.
- Sections get stable `id`s (`gw-<n>` / `date-<d>`), which also enables
  future deep links at no extra cost.

## Section 3 — Legibility
- Records club columns print full team names (uppercase Archivo caps, as now)
  with real crests via `TeamBadge info=` at `md` size; `title` attribute
  carries the full name under truncation. Same treatment both groupings
  (gameweek and date-fallback).
- Empty, offline, and error states keep their copy and behavior; only rows
  change. No endpoint changes anywhere.

## Testing
- Unit tests for `currentGameweek` (contains-today, upcoming fallback,
  latest fallback, empty input).
- Endpoint shapes unchanged; `tsc`, `eslint`, and the impeccable detector
  pass on touched files.

## Out of scope
- URL deep-linking/query params, dropdown pickers, settings, admin UI.
- Any change to verdict computation, calibration, or forecast logic.
