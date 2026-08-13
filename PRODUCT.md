# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Existing codebase: React 19 + Vite + TypeScript + Tailwind CSS frontend, FastAPI backend, deployed via Vercel.

## Users

Primary: data and machine-learning enthusiasts — people who find the model as interesting as the predictions. They come to see how a Random Forest prices football matches, what features it leans on (ELO, rolling xG form), and how it actually performs against results. They want to verify claims, read methodology, and browse matchday verdicts with the confidence of someone who understands what's underneath. Confirmed by user: casual fan browsing and betting-odds comparison are secondary, not driving audiences.

## Product Purpose

Predicts Premier League match outcomes with an ML pipeline (Random Forest regressors on 5 seasons of history, with ELO ratings, rolling goals + xG form, and team encoding) and presents each matchday's verdicts as a browsable site. Success means a visitor understands the model, trusts its honesty (including where it was wrong), and can see every fixture of the current matchday with probabilities and expected scorelines.

## Positioning

The model is the product. Where a typical prediction site hides its engine behind glossy odds, this site shows its work: named features, stated accuracy, live verification against real results, and the raw probability breakdown for every fixture. The mechanism no competitor could copy-paste is the honest, auditable model — predictions presented as a scientific readout of the game, not a bookmaker's tip.

## Operating Context

- Matchday ritual: fixtures land, the morning automation generates predictions, visitors check the gameweek's slate.
- Evening automation compares predictions against actual results — this verification data is real and must be surfaced honestly (wins and misses).
- Dev workflow: `python -m backend.server` (FastAPI on :8000) + `npm run dev` (Vite on :5173, proxying /api to localhost:8000); prod serves API and frontend same-origin via Vercel.
- Data available via API: `/api/matches/all` (all matches with predictions + gameweeks), `/api/matches/predictions?date=`, `/api/matches/results?date=`, `/api/teams`, `/api/matches/upcoming`, `/api/dates/available`, `/api/health`.
- Match shape: `{ id, date, time?, gameweek?, home_team, away_team, home_team_info?, away_team_info?, prediction?, status?, score? }`; prediction: `{ prob_home, prob_draw, prob_away, score?, winner?, home_goals?, away_goals? }`.
- Team badges come from backend-served `badge_url` (with initials fallback). No other image assets exist.

## Capabilities and Constraints

- One deployed product: single-page React app currently; user confirmed the site should expand (matchday predictions as core, plus how-the-model-works and accuracy/verification content).
- Existing endpoints and data shapes are the contract; redesign must not break them and must not invent new product behavior.
- Backend may be offline in dev → the UI must keep a graceful offline state.
- WebGL/three, motion, lucide-react, Tailwind 3 already in the stack; heavy effects are optional, not required.
- Vercel serverless deployment: no long-lived processes on prod.
- Undecided: whether home/away goal probabilities (Poisson) get their own visualization; whether the model page includes trained weights or only methodology prose.

## Brand Commitments

- Product name: "Football Predictor" (header wordmark "Football Predictor", logo "FP" monogram). No external logo, no registered marks.
- User asked for a full reinvention of the visual world — the incumbent dark "stadium night broadcast" look is not binding.
- Voice: honest, technical, confident; the model's accuracy is shown, not overstated.

## Evidence on Hand

- Real data: `data/teams.json` (20 PL teams + badge URLs), `data/predictions/`, `data/results/` (result comparisons), model artifacts (`model_home.pkl`, `model_away.pkl`, `team_encoder.pkl`, `training_data.pkl`), and the live backend API in the repo.
- Design-intent docs: `docs/superpowers/specs/2026-08-10-frontend-redesign-matchday-broadcast-design.md` and `2026-08-11-animated-background-dither-motes-design.md` describe the incumbent (rejected) world — evidence of what the site was, not authority.
- No testimonials, press, benchmark claims, or third-party logos exist. These must not be fabricated.

## Product Principles

1. Show the work: the model's features, inputs, and verdicts are visible, not hidden behind presentation.
2. Honest verification: accuracy and past results are shown including misses — credibility is the product.
3. The model leads, the game follows: football facts (teams, fixtures, scores) serve the prediction readout, not the other way around.
4. Scanable matchdays: a visitor can read an entire gameweek's verdicts at a glance.
5. Technical audience respect: precision, legibility, and density are welcome; gimmickry is not.

## Accessibility & Inclusion

No product-specific requirement established beyond baseline web accessibility (semantic HTML, keyboard operability, reduced-motion support, sufficient contrast).
