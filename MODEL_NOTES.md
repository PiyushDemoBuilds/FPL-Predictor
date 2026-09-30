# Model notes — external review adoption (Aug 2026)

Context: an external review benchmarked this codebase against commercial
predictors (Fantasy Football Hub, FPL Review MDM, Fantasy Football Fix, FPL Scout)
and the OpenFPL paper (2025), which found commercial services' edge concentrates
in 0-2pt games via proprietary minutes/news intel, while public-data models
match them on 3+pt haulers. Items adopted, with validation:

## Adopted this pass

1. **Learned minutes/availability model** (replaces the hand-tuned formula)
   `MinutesModel`: XGBoost P(starts), P(plays 60+), E[minutes] on the same
   leakage-safe features. OOS 2025/26 (expanding window):
   **start AUC 0.944 · min60 AUC 0.941 · minutes MAE 13.2**.
   Drives xminutes, nailed, the availability factor and captain scoring.
2. **Distributional shape / uncertainty** (ceiling & floor, not just means)
   `ShapeModel`: P(haul ≥8) and P(blank ≤1). OOS: **haul AUC 0.878 ·
   blank AUC 0.919**. Captain table shows Floor/Ceil %; SAFE = floor-first,
   CEIL = highest boom probability (pundit "safe armband, risky ten" logic).
3. **MILP transfer optimization** (bug fix: the old search never actually
   evaluated 2-transfer plans despite its docstring). `transfer_plans_milp`
   solves exact 0/1/2-swap plans under budget, ≤3/club, 2/5/5/3, hits at −4,
   pundit buy-filter, horizon-EV objective (PuLP/CBC; heuristic fallback
   now also enumerates 2-move combos). `build_squad_milp` gives the exact
   optimal squad for drafts.
4. **Dynamic chip planning** (bug fix: `squad_ev` was ignored). Bench Boost /
   Triple Captain advice now computes YOUR bench/captain projected points in
   the next DGW from the fixture list, with STRONG/decent/weak verdicts and
   chips-remaining from your entry history. (No DGW/BGW in the current
   2026/27 fixture list yet — advice says so honestly and re-checks weekly.)
5. **Team-scaled set-piece weights**: pen value scales with team attacking
   volume (0.7-1.4×) — a stand-in for true team penalty frequency, which no
   free source exposes.
6. **Price-move signals**: FPL's own `price_change_projections.likelihood`
   surfaced as ▲rise/▼fall tags ("buy early / sell early" timing).

## Deferred (with reasons)

- **Betting-odds features** (Dixon-Coles team goals/CS probabilities): the
  strongest remaining gap vs commercial feeds, but there is no free reliable
  historical odds API; a keyed fetch could slot into `features.build` as
  `f_odd_*` team columns — hook documented, not implemented.
- **Understat shot-level xG**: the public pages now load data via XHR
  (not in HTML), so scraping needs a headless browser; FPL's own xG/xA
  already covers most of the signal at team level.
- **Chip-timing as a dynamic program**: needs DGW-aware future fixtures
  (they don't exist until cups play); the dynamic chip planner above is the
  practical subset. Revisit when 2026/27 DGWs appear.
- **Price-change prediction model**: FPL now publishes rise/fall likelihoods
  directly (adopted via #6); a bespoke net-transfer model would add little.

Validation harness: `python tests/streamlit_test.py` renders every dashboard
page headlessly and fails on an application exception.
