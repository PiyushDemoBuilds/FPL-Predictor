# Problems found in the original FPL Assistant (v1)

Reviewed from: README.pdf, USER_GUIDE.pdf, FPL_Analytics_MBA_Submission.pdf, dashboard_preview.pdf.
Each item below was verified against the data or the notebook code.

## 1. The "beats FPL's own xP" baseline was partly broken
- vaastav's `xP` column **silently stops being computed mid-season**: 83% of 2025/26 rows are exactly `0.0`
  (e.g. Bruno Fernandes has real xP until GW9, then 0.0 forever). Other seasons: ~40% zeros.
- The notebook used this column both as a **top feature** (`feat_fpl_xp`) and as the **baseline** the
  models "decisively beat" (MAE 1.06, Spearman 0.31, DM −18.9). A baseline that is 0.0 for 83% of rows
  is trivial to beat — the headline claim is inflated.
- **Fix in v2:** zeros → NaN; the expectation feature is never-missing (`f_expect`) with a trust flag;
  baselines are vaastav-xP-on-valid-rows *and* a naive last-3-form baseline; honest notes in the report.

## 2. Hurdle model math bug (inherited straight into the notebook)
- `p1 * E[y|y>0] − SHIFT` drops the zero-mass term. Correct: `p1 * (E[y|y>0] − SHIFT)`.
- With the bug, MAE ≈ 3.8 despite the best ranking (Spearman 0.742). The README called the hurdle
  "best MAE/ranking" — impossible with this formula.
- **Fix in v2:** corrected; hurdle now has the best MAE (0.796) *and* best Spearman.

## 3. Trained on per-fixture rows, not player-GW rows
- vaastav `merged_gw` has **one row per fixture**. In DGWs a player has 2 rows with the same GW —
  the rolling features and labels then mix fixture-level and GW-level quantities, and DGW rows
  double-count.
- **Fix in v2:** everything aggregated to player-GW rows with an `n_fix` feature and summed difficulty —
  DGWs are modelled instead of corrupting the windows.

## 4. Team one-hot features don't survive promotion
- The notebook keeps `feat_team_{id}` one-hots. Promoted clubs' players are all-zeros vectors at
  prediction time — the model has never seen that combination. The assistant's README even says the
  dummies were turned off by default; the notebook (the "final submission") still used them.
- **Fix in v2:** continuous team/opponent strength (rolling xG/xGA/GF/GA/CS + prior-season strength,
  promoted clubs imputed at a weak tier).

## 5. GW1 cold-start blow-ups (why GW1 didn't help)
- GW1 projections were essentially prior-season points-per-game with no shrinkage, no price prior and
  no trust weighting — the dashboard preview showed Haaland 17.0, Thiago 16.0, Ndiaye 16.0 (actual: 2, 0, 9).
  The user guide admits "GW1 numbers run a bit hot": −17 pts on one captain pick alone.
- **Fix in v2:** shrunk prior-season aggregates (minutes-based shrinkage toward position mean), a
  price-implied prior for brand-new signings, form carried across the season boundary, isotonic
  calibration, and an early-season blend with FPL's own `ep_next` (weight 30% at GW2, 18% to GW4).

## 6. 3-GW label leakage in the backtest (and no purging for the Tweedie model)
- Training rows at GWs k−2/k−1 have `label_3gw` windows that include the test GW k. The README claims
  purging existed in the assistant; the notebook never purges.
- **Fix in v2:** 3-GW training rows require GW ≤ k−3 and the early-stopping validation set is also purged.

## 7. Simulation & optimizer didn't match the real game
- `initial_squad` in §6 has no reservation pricing (can strand the budget / produce illegal squads —
  fixed only in the §10 cold-start version); the season sim picks a **top-11 by projection that isn't
  formation-legal** (can start 2 GKs); `captaincy_sim` rebuilds the squad *every GW* on that GW's
  projections — implicitly unlimited free transfers, inflating all absolute totals.
- Transfer logic assumed **1 free transfer/week with −4 hits** — FPL has moved to **5 rolling free
  transfers** (`max_extra_free_transfers = 4` in the current game settings). Chips: every chip is now
  playable **twice** (pre-GW20 window + post-GW20 window per the API). Sell-on fee 0.5 not modelled.
- **Fix in v2:** reservation-aware builder + improvement passes; 8 legal formations; horizon-EV transfer
  planner with the 5-FT bank, hits and budget incl. bank; chip planner aware of doubled chips.

## 8. Speed
- Serial fetching of ~600 element-summary endpoints (minutes per refresh), no TTL cache, CSV storage.
- **Fix in v2:** 24-thread concurrent fetch (all 612 summaries in ≈2–4 s), TTL disk cache keyed by
  completed-GW signature, parquet storage, end-to-end weekly update ≈60 s including retraining.

## 9. Smaller issues
- Early stopping validated on the single most recent GW (noisy) → last-3-GW validation in v2.
- `local_team_ids` "id a team never faces" trick is fragile (breaks with cup/dup rows); replaced by
  canonical name bridging.
- Relagated-club players mapped to team id 0 in the notebook (visible as "T0" clubs in its own output);
  v2 keeps them under stable synthetic ids.
- FPL `ep_next` (the live xP the official game publishes every week) was never used at inference; v2
  blends it in early season and shows it next to model projections.

## What v1 got right (kept)
Leakage discipline (shift-1 rolling features), code→player-id bridging, expanding-window evaluation,
DM testing, adaptive model selection by job (ranking vs expectation), the feedback-loop idea, and the
general architecture. v2 is a rebuild of the weak parts on the same sound skeleton.
