
# FPL Predictor

**FFH-style dashboard (Streamlit + Plotly)** at `http://localhost:7860`: sidebar navigation (My Team & AI Rating · Transfer
Planner · Player Explorer · Fixtures & Odds · Model Diagnostics), an
interactive 2D pitch with captain badges and injury flags, an AI team-rating
gauge (0-100 with attack/availability/fixture sub-scores), MILP transfer
plans with one-sentence rationale chips, a 5-GW projection grid, an
effective-ownership risk quadrant, and a click-through player profile
drawer (per-GW bars, floor/ceiling, underlying stats). Diagnostics
(Spearman/DM) live exclusively on the Model Diagnostics tab. All charts are
interactive Plotly (gauge, quadrant scatter, per-GW bars, FDR heatmap); the
pitch is a custom HTML/CSS component. Test the dashboard headlessly with
`python tests/streamlit_test.py`.

A faster, sharper FPL predictor: live API pipeline (concurrent + cached), leakage-free XGBoost
models with isotonic calibration, a 2026/27-rules squad/transfer/captain optimizer, season planner
(DGW/BGW/double-chips), and a web dashboard. Team ID preconfigured: **6749446** (XGBoost United).

## Quick start (Windows)

1. Install Python 3.10+ from python.org (tick **Add to PATH**).
2. Double-click **SETUP.bat** — installs packages, downloads 4 seasons of history + live data,
   trains the models, and produces your first GW analysis (2–5 minutes).
3. From then on, double-click **START_DASHBOARD.bat** and use the browser at
   `http://localhost:7860`. No terminal needed.

Mac/Linux: `pip install -r requirements.txt`, `python cli.py setup`,
`python cli.py serve`.

## Projections, honestly calibrated
Live xPts = per-position-isotonic-calibrated poisson+hurdle blend, certainty-
blended with the component model (xMins/90 x learned pts/90), soft-capped at
11 — the single-GW top end lands in the mid-4s this week because that is the
true out-of-sample conditional mean (FPL's own ep_next tops at ~4.0);
commercial sites showing 8+ for the same players are un-calibrated rankings.
DGWs will naturally push doubling players toward 7-10. Every run validates
ETL (100% id/club/position match vs bootstrap) before projecting.

### Prediction integrity (v3)

- The weekly validator checks duplicate **player-GW** observations, not repeat
  appearances by a player across normal historical gameweeks.
- Model early stopping now uses a disjoint final three-calendar-GW window;
  older seasons are decayed by elapsed time rather than matching GW number.
- The live single-GW number is exactly the walk-forward-tested,
  per-position-calibrated Poisson+hurdle ensemble. It is no longer mixed with
  unvalidated component or 3-GW predictions after calibration.
- Transfer recommendations use the legal starting XI plus captain each week,
  so bench projections no longer receive starter-level value.

## The weekly routine (100 seconds)

After each gameweek finishes (usually Tuesday night UK), open the dashboard and click
**↻ Update everything**. That single button:

- pulls fresh prices, ownership, news, injuries and the just-played GW (concurrent fetch, seconds),
- retrains on 4 historical seasons + this season's played GWs (recency-weighted),
- refreshes GW / 3-GW / 5-GW projections for all ~612 players (with expected minutes),
- re-analyses **your squad**: best XI, captain table, transfer plans scored on a 5-GW horizon
  under the 5-free-transfer rule, and
- updates the season plan (DGW/BGW watch, chip strategy, fixture grid),
- logs predicted-vs-actual for your team and self-calibrates next week.

`UPDATE_WEEKLY.bat` does the same thing headless if you prefer.

## What the numbers mean

- **Proj** — expected points next GW (calibrated). Use for *ranking* (picks, captain), not as guarantees.
- **3-GW / 5-GW** — per-GW average over next 3 / total over next 5. Use for transfer decisions.
- **xMin** — expected minutes; low values = rotation/injury risk (projection already scaled by it).
- **Pills** — fit / 75% / out, driven by FPL's `chance_of_playing_next_round` and status.

## Model (v2) — what changed and why

Backtest: expanding window over 2025/26 GW2–38, label purging for 3-GW targets, recency-weighted
training, last-3-GW early stopping. Hurdle 1-GW: **MAE 0.796, Spearman 0.742**; Tweedie 3-GW:
**MAE 0.74, Spearman 0.789**. Captain top-3 hit ≈ 62% vs 8% for naive form. Isotonic calibration
fitted out-of-sample. Full list of v1 problems fixed: see `PROBLEMS_FOUND.md`.

Dashboard: interactive Insights (SVG charts — hover tooltips, click-to-filter, position-legend
toggles, a draggable ownership threshold for differentials), a persisted **shortlist** with
combined cost/projection, why-columns (opponent + FDR, xMin, nailed, set-piece, price risk),
**team-value tracking** (squad + bank + Δ vs last GW) on My Team, and a live model/GW footer.
Live 1-GW model is a **50/50 poisson+hurdle blend** (best captain top-3 hit: 74% vs 62/67% either
alone) with **per-position isotonic calibration** (MAE 0.839 vs 0.849 global, 2025/26 OOS).
Availability & shape: learned **P(start)/P(60+)/E[mins)** classifiers (OOS AUC 0.94)
drive xMin/nailed/captaincy, with **floor/ceiling** probabilities per player
(haul/blank AUCs 0.88-0.92). Transfers are solved as **exact MILP** 0/1/2-swap
plans (PuLP/CBC, heuristic fallback), and chip advice is computed from your
squad's projected DGW value. See `MODEL_NOTES.md` for the external-review
adoption list and deferred items (odds feed, Understat, chip DP).
Tests: `python tests/streamlit_test.py` renders every dashboard page headlessly.

Pundit-grade decision layer (see **PUNDIT_PLAYBOOK.md** for the research → implementation mapping):
set-piece/penalty features (pens ≫ corners, backups discounted), a 0-100 "nailed" minutes-security score,
champion-style captain scoring (EV × minutes-security + penalty upside, SAFE/DIFF tags), squad-structure
check vs the elite template (3-4 premiums, playing enablers, bench ≤ £20m), autosub bench order,
price-rise/fall risk tags, and a "protect your 5-FT bank" hold recommendation.

Key upgrades: DGW-safe player-GW aggregation; no team one-hots (promoted clubs generalise);
never-missing expectation feature with trust flag (the broken vaastav xP column is neutralised);
hurdle math corrected; availability factor from expected minutes; early-season blend with FPL's own
`ep_next`; 2026/27 rules (5 FT bank, doubled chips, 50% sell-on fee).

## Layout

```
SETUP.bat / START_DASHBOARD.bat / UPDATE_WEEKLY.bat / REVALIDATE_MODEL.bat
cli.py           terminal commands (setup|update|backtest|team|plan|serve|status)
app.py           Streamlit dashboard -> http://localhost:7860
src/fpl/api.py       concurrent FPL API client + TTL cache
src/fpl/history.py   vaastav + live data -> one canonical player-GW table
src/fpl/features.py  leakage-safe features (~64)
src/fpl/models.py    model zoo, backtest, isotonic calibration
src/fpl/optimizer.py squad builder, XI, transfers (5-FT rules), captain
src/fpl/planner.py   fixture grid, DGW/BGW, doubled-chip advice
src/fpl/myteam.py    your squad, feedback loop, calibration
src/fpl/pipeline.py  the one-click weekly orchestration
config.json      team id + knobs
data/            cache + parquet (auto-managed)
outputs/         projections, team reports, plans, backtest
```

## Notes

- The official API serves the current season; history comes from
  vaastav/Fantasy-Premier-League (downloaded once, cached).
- Predictions are a decision aid — always check team news before the deadline.
