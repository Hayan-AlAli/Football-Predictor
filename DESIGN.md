---
name: The Matchday Almanack
description: Premier League predictions printed as a season's yearbook, set in ink on warm cream paper — ruled ledger pages, rubric-stamped verdicts, machine-set figures.
colors:
  paper: "#F1E9D8"
  paper-deep: "#E9DFC8"
  paper-white: "#FFFFFF"
  line: "#C9BD9F"
  ink: "#2A2A29"
  ink-soft: "#4A463F"
  ink-faint: "#6A6355"
  rubric: "#B93B2F"
  rubric-deep: "#A0392D"
  ledger: "#2F6E48"
  ledger-deep: "#316B4A"
  ledger-bright: "#3E9C6E"
typography:
  display:
    fontFamily: "Archivo, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "clamp(1.75rem, 4.5vw, 2.75rem)"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Archivo, sans-serif"
    fontSize: "clamp(1.375rem, 3.5vw, 1.875rem)"
    fontWeight: 700
    lineHeight: 1.15
  title:
    fontFamily: "Archivo, sans-serif"
    fontSize: "clamp(1.125rem, 2.5vw, 1.375rem)"
    fontWeight: 700
    lineHeight: 1.15
  body:
    fontFamily: "Archivo, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "'Fragment Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.6875rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.14em"
rounded:
  none: "0px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  two-xl: "48px"
  three-xl: "64px"
components:
  button-print:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "10px 16px"
    typography: "{typography.label}"
  button-print-hover:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.rubric}"
    borderColor: "{colors.rubric}"
  button-print-active:
    transform: "translateY(1px)"
  button-turn:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    size: "40px"
  button-turn-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  stamp:
    backgroundColor: "{colors.rubric}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    padding: "4px 8px"
  chip:
    backgroundColor: "transparent"
    textColor: "{colors.ink-soft}"
    typography: "{typography.label}"
    borderColor: "{colors.line}"
  ledger-row:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    padding: "16px 8px"
  ledger-row-hover:
    backgroundColor: "rgba(42, 42, 41, 0.04)"
  plate:
    backgroundColor: "{colors.paper-deep}"
    textColor: "{colors.ink}"
    borderColor: "{colors.line}"
  nav-link:
    textColor: "{colors.ink-soft}"
    typography: "{typography.label}"
  nav-link-active:
    textColor: "{colors.rubric}"
    borderBottomColor: "{colors.rubric}"
---

# Design System: The Matchday Almanack

## Overview

**Creative North Star: "The Statistical Yearbook"**

The site is the season typeset as a printed yearbook that the model itself prints. Every matchweek is a ruled ledger page; the model's call on each fixture is stamped in rubric red; the machine's figures are set in Fragment Mono. The reader is an archivist auditing the press: they open the book at this matchweek, read the day's verdicts in seconds, turn to METHOD to audit the engine, and to RECORDS to see where it was wrong. Honesty is physical: misses print beside hits, empty pages say they are empty.

The world is flat print, not screen craft: warm cream paper with a fixed fibre-grain sheet, ink at hairline weight, square corners, no glass, no glow, no gradient. Depth is the thickness of a book — a plate lifted a shade off the page, a stamp pressed a fraction into it. Contrast is the legibility floor the theme was restored for: ink-black type on cream at ~15:1, small print at ~5:1, and the two accents deepened so the smallest readouts pass 4.5:1. Confirmed anti-references: the dark "night edition" (rejected by the user — the black-text-on-dark inversion failures); the earlier "stadium night broadcast" look; generic dashboard aesthetics (cards, metric tiles, gradients, glass).

**Key Characteristics:**
- Cream paper, ink-black type, one rubric accent and one ledger-green accent, nothing else
- Hairline rules (1px) do all separating; double rules open sections
- Every number is a machine figure: tabular, mono, uppercase where it is a label
- Motion is print registers: rules draw, stamps press, folios tick, pages turn
- Empty and offline states are honest book pages, not error screens

## Colors

Ink type on warm cream paper, with two accents that never compete: rubric red is the model's call (authority), ledger green is the machine's record (verification). All neutrals are warm-toned from the paper and the ink, never gray.

### Primary
- **Rubric Red** (#B93B2F, deep #A0392D): the model's verdicts, at ~4.7:1 with paper text on the stamp block and ~4.6:1 as small text on paper (WCAG AA passes; the previous #C14335 failed at ~4.2:1). Stamps ("FP" monogram, outcome calls), active nav underline, focus rings, selection tint, the press-fill loader, links (deep). Authority appears sparingly — it prints what the model decided, nothing else.
- **Ledger Green** (#2F6E48, deep #316B4A, bright #3E9C6E): the machine's verification record, at ~5:1 on paper (the previous #3F8F5B failed at ~3.3:1). CORRECT verdict stamps in Records, correct-count readouts, the method page's margin-note callout. Never used for the model's calls themselves.

### Neutral
- **Paper** (#F1E9D8): the warm cream page ground, with **Paper Deep** (#E9DFC8) for plates and folded sheets (a shade deeper — the plate sits into the page), **Paper White** (#FFFFFF) for buttons, chips, and badge plates that lift off the page (white crest images blend seamlessly), and **Line** (#C9BD9F) for hairlines.
- **Ink** (#2A2A29): ink-black — text and rules at full weight (~15:1 on paper); **Ink Soft** (#4A463F) for body copy (~8:1); **Ink Faint** (#6A6355) for folios, small print, and run labels (~4.9:1 on paper, ~4.5:1 on plates).

### Named Rules
**The Rarity of Red Rule.** Rubric renders only where the model pronounces: stamps, the active section, links, and loaders. If a surface needs a third emphasis, it is weight or size — never a new color.
**The Warm Neutral Rule.** Every neutral is tinted from the paper or ink hue. Plain gray (#808080) never appears; placeholder and disabled states use ink-faint, not gray.

## Typography

**Display Font:** Archivo (weights 400–800, loaded from Google Fonts) — the book's type: squared grotesque caps for headings and wordmark.
**Body Font:** Archivo — book text at 1.7 line-height.
**Label/Mono Font:** Fragment Mono — every figure, folio, label, and readout, 0.6875rem, uppercase, tracked 0.14em.

**Character:** The book is set by a machine: headlines in heavy-tracked Archivo caps, all numbers and labels in Fragment Mono so figures read as figures, and Spectral italics for the archivist's margin annotations (page intros, plate notes). Three voices, three jobs.

### Hierarchy
- **Display** (Archivo 800, clamp(1.75rem, 4.5vw, 2.75rem), 1.15): section titles ("The Matchday Almanack", "The Method", "The Records"), all-caps with 0.08em tracking.
- **Headline** (Archivo 700, clamp(1.375rem, 3.5vw, 1.875rem), 1.15): page-level headings.
- **Title** (Archivo 700, clamp(1.125rem, 2.5vw, 1.375rem), 1.15): plate headings, station titles.
- **Body** (Archivo 400, 1rem, 1.7): paragraph copy in ink-soft, measure 65–75ch, max-width ~65ch.
- **Label** (Fragment Mono 600, 0.6875rem, tracking 0.14em, uppercase): folios, running heads, chips, stamps, button labels, table heads.
- **Large folio numerals** (Fragment Mono 600, text-5xl/6xl ≈ 3–3.75rem, tabular): the matchweek numeral on the page-turn nav.
- **Annotation** (Spectral 400–500 italic, 1rem): marginalia under headings and inside plates.

### Named Rules
**The Figure Rule.** Any number that carries data — folios, matchweeks, ELO, probabilities, scorelines — is set in Fragment Mono with `font-variant-numeric: tabular-nums`. Archivo numerals appear only where a number is part of prose.
**The Label Rule.** Labels are Fragment Mono, 0.6875rem, uppercase, 0.14em tracked, ink-faint at rest. A label never sits above a heading as an eyebrow; running labels belong to book furniture (folios, rules), not headlines.

## Layout

A single book column: `max-w-5xl` (64rem) page with `px-4` margins, flex column root, and a sticky running head. Sections are opened by double hairlines (`rule-double`), rows separated by single hairlines. Spacing is a 4px-based rem scale (4/8/16/24/32/48/64); rhythm uses tight groups with generous separation, more space above a heading than below.

The ledger row is the core unit: a full-width grid row (badges, names, H/D/A readout, expected scoreline, call) with `gap-x-2` on mobile, `gap-x-3` with an extra readout column at `sm`. The matchweek nav centers a large folio numeral flanked by square page-turn buttons; on mobile the adjacent-matchweek previews collapse (density drop, not rearrangement). Teams Index and Records use the same row grammar with different columns. Content maxes at ~65ch in prose plates; tables span the full page width.

## Elevation & Depth

The world is flat print; depth is book thickness, expressed by two shadows only. Surfaces sit flat at rest; nothing glows or floats. On the cream ground, the plate's edge is an ink hairline and the stamp's under-edge is a dark press line.

### Shadow Vocabulary
- **Plate shadow** (`0 1px 0 rgba(42, 42, 41, 0.08), 0 8px 24px -12px rgba(42, 42, 41, 0.3)`): the fold-out plate lifted off the page — an ink catch-light on the edge, a soft ambient under the sheet.
- **Press shadow** (`0 2px 0 rgba(42, 42, 41, 0.16)`): the stamp's hard under-edge, cutting the bright block from the page (rubric-tinted on button hover).

### Named Rules
**The Flat-By-Default Rule.** No elevation at rest beyond the two book shadows. Hover states change ink and ground (btn-turn inverts to ink; ledger-row warms to a faint ink-tinted ground), they never lift.

## Shapes

Square corners throughout — radius is always 0, the world is letterpress, not plastic. Separation comes from 1px hairlines (`--line`), never from rounding. Stamps and chips are sharp rectangles with hard padding (4px 8px stamps; 3px 7px chips). The page-turn button is a 2.5rem square. The one recurring silhouette beyond the rectangle is the stamp — solid rubric (or ledger green) block with paper text and a press under-edge — and the fold-out plate, a paper-deep panel with a hairline border and plate shadow that unfolds under its ledger row.

## Components

### Buttons
- **Shape:** square (0 radius), hairline border.
- **Primary — Print Button:** white paper ground, 1px ink border, Fragment Mono 0.75rem uppercase 0.12em tracking, 10px 16px padding. Hover: rubric text + rubric border + rubric press shadow. Active: translateY(1px). Disabled: opacity 0.38, pointer-events none.
- **Page-Turn Button:** 2.5rem square, white paper ground, 1px line border, ink glyph. Hover (enabled): inverts to ink ground with paper glyph. Disabled: opacity 0.35.

### Stamps
- **Style:** solid rubric (or ledger green for CORRECT verdicts) block, cream paper text (inverting the bright block), Fragment Mono 0.6875rem uppercase 0.14em, 4px 8px 5px padding, press shadow under-edge (~4.7:1). Enters via stamp-press (scale 0.82 → 1, 0.34s print curve).
- **Use:** model's call on each fixture row, the "FP" monogram, verdict stamps in Records.

### Badges
- **Style:** real club badge (from `badge_url`) in a white 1px-lined frame — white crest images blend into the cream page; when the image fails or is absent, the club's initials print on the club color. The initials' ink is luminance-adaptive: cream on dark club inks, ink on bright ones (Wolves yellow, Hull orange) — text must never sink into the plate.

### Chips
- **Style:** transparent ground, 1px line border, Fragment Mono micro label, ink-soft text, 3px 7px padding. Used for season, gameweek, and count readouts.

### Cards / Containers
- **Plates:** paper-deep ground, 1px line border, plate shadow, square corners, internal padding on the md/lg scale. Only container form in the system (fold-out details, method plates, offline/empty states).

### Ledger Rows
- **Style:** full-width ruled grid row, hairline separators, 16px vertical padding, `gap-x-2`/`gap-x-3`. Hover: `rgba(42,42,41,0.04)` ink-tinted ground. Columns: badge (2.75rem) · home · readout · away · call (desktop adds a 10rem readout column at `sm`).

### Navigation
- **Book sections:** Fragment Mono micro labels, uppercase, ink-soft at rest; active section is rubric with a 2px rubric bottom border. Page-turn nav: folio numeral flanked by square buttons, previous/next with aria labels.

### Motion
- One authored register per element, all on the print curve `cubic-bezier(0.22, 1, 0.36, 1)`: rules draw (scaleX), stamps press (scale 0.82→1), folios tick (translateY), ledger rows stagger in at 50ms, pages turn (rotateY 4° on a left origin). Loader is the press-fill (rubric bar translating along a 2px track, 1.4s). Full `prefers-reduced-motion` path kills every animation and freezes the loader to a line.

## Do's and Don'ts

### Do:
- **Do** set every figure in Fragment Mono with tabular figures — folios, matchweeks, ELOs, probabilities, scorelines.
- **Do** separate with 1px hairlines in `--line`; open sections with double rules; keep all corners square.
- **Do** reserve rubric for the model's pronouncements (stamps, active nav, links, loaders) and ledger green for verification (CORRECT verdicts, counts).
- **Do** write empty and offline states as honest book pages that name the absence and the recovery ("The press has nothing printed on this page of the ledger").
- **Do** keep every text/accent pairing at 4.5:1 or better on the cream ground — small readouts use ink-faint or the deep accent variants, never the bright ones.
- **Do** animate on the print curve with a start state that exists at rest (drawing rules, pressing stamps); honor reduced motion completely.

### Don't:
- **Don't** use cards-with-icons, metric tiles, gradient text, glass blur, glow, or anything from the rejected broadcast world.
- **Don't** put a kicker or eyebrow above a heading — the heading carries the page.
- **Don't** use colored or wide left borders on callouts (the method page's ledger-green margin note is an annotation within print, not a house style).
- **Don't** introduce new accent colors; red and green are the only inks beyond ink-on-paper.
- **Don't** use hard offset shadows (4px 4px 0) — the press under-edge is the world's only block shadow.
- **Don't** let rubric cover more than a stamp, an active link, or a loader at once.
