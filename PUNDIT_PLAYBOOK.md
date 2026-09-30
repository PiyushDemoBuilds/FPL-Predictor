# PUNDIT PLAYBOOK — what proven FPL managers prioritize, and where FPL Edge implements it

Researched from interviews and guides featuring managers with verified long-term results.
Every principle below is mapped to a concrete feature in this project.

---

## The sources (verified track records)

| Manager | Credentials | Core philosophy |
|---|---|---|
| **Erik Ibsen** (@FPL_Study) | World #1 in 2025/26 (OR 1 of 13.1m, 2,582 pts) | Form + fixtures; risk-averse captaincy; consistency over gambling; chips around DGW/BGW clusters |
| **Walter Randazzo** | 7× top-10k finishes | Underlying data (xG, chance involvement) + FDR + rotation + injury; plan 6 weeks out, stay flexible |
| **Keyuran Govender** (@FPL_Keys) | Best OR over 2023-25 (13 & 229) | Minutes, big chances, CS potential, price-change timing, hold-horizon per transfer |
| **Top-0.1% managers** (r/FantasyPL) | verified flairs | Nailed starters ~95% of picks; fewest hits; save FTs; wait for Friday team news; play template early |
| **The Athletic / vice-captain.com set-piece guides** | — | Set-piece duty is the cheapest information edge; pens ≫ corners; backup taker worth a fraction |
| **FPL Hints 2026/27 guide** | — | Captaincy checklist: fixture, expected minutes, penalty duties, goal involvement, home adv, opponent defence |

## The 10 rules and their implementation

### 1. "Minutes come first, always" (every elite manager)
- **In the model:** minutes/streak/start-rate features + shift(1) rolling windows; **xMin** and a 0-100
  **Nailed** score per player; projections multiplied by an availability factor — a fringe GK "projecting"
  4 pts over 20 minutes gets scaled to ~1.5.
- **In the UI:** Nailed + xMin columns; captain table penalises minutes risk.

### 2. Safe captaincy, risky other ten (Ibsen)
- **CaptainScore = EV × (0.75 + 0.25·nailed) + penalty upside** — favours secure, penalty-taking assets;
  tags **SAFE** (top score) vs **DIFF** (low ownership, ≥80% of top score). GW2 output: Thiago SAFE
  (nailed 99, pens) ahead of Haaland (nailed 71, xMin 59) — precisely the champion's risk logic.

### 3. Form + fixtures, in that order (Ibsen: "form and fixtures")
- Exponentially-weighted form (decay ~3 GWs) × official FDR + opponent rolling xG/xGA/GF/GA/CS rate;
  2026/27 fixture grid with DGW detection. Transfer plans are scored on a **5-GW horizon** ("plan 5-6
  weeks out" — Ibsen; "at least 4" — Randazzo).

### 4. Underlying stats over last week's points (Randazzo, FFGeek)
- xG/xA/xGI per 90, shots-proxy (threat, BPS, ICT), blank/haul rates — never raw recent points alone.
  GW1 burn victims (your 33 pts) are exactly what this protects against.

### 5. Set pieces: pens ≫ free kicks > corners (The Athletic, vice-captain.com)
- **New features** `f_sp_pen / f_sp_fk / f_sp_corner / f_sp_score` built per season from
  players_raw/bootstrap `*_order` fields (first-choice = 1.0, backup = 0.3-0.4 — "the second name is
  worth a fraction of the first"). Feeds both the model and a league-wide **set-piece takers table**.

### 6. Squad structure: 3-4 premiums, playing enablers, cheap bench (multiple guides)
- **Structure card** in My Team: premiums £9m+ / mid-tier / playing enablers counts, bench spend vs the
  ~£20m elite norm, deadwood flags, and autosub bench order (outfield by projection, GK last).
  Your squad currently flags 4 non-playing bench assets and dead money.

### 7b. Pundit filter + verdicts on every suggestion
- **Buy candidates must be fit (status/chance ≥75%) and nailed ≥55** — rotation-risk and injured
  players can't enter transfer suggestions at all. Every plan carries a verdict: **STRONG** (≥8 pts
  horizon EV, free), **SOLID** (4-8), **MARGINAL** (<4 → the dashboard says hold and bank the FT).

### 7. Free transfers are precious — take fewest hits (top-0.1% managers)
- Transfer planner models the **5-FT bank** (2026/27 rules), prices hits at −4, and shows a
  **"no transfer is also a transfer"** hold recommendation when the best plan gains < 4 pts over the
  horizon. Plans always include the 0-transfer option.

### 8. Price-change timing (Govender)
- Price momentum features (`f_val_chg3`, transfers-in EWM) in the model; ▲/▼ **price-risk tags** in the
  projections table from the live `cost_change_event` / price-change projections.

### 9. Play the metagame: template anchors + calculated differentials
- Ownership is a model feature; Insights tab separates must-own value from **differentials** (<8%
  owned, high proj). Captain table flags DIFF options with ≥80% of the safe pick's score.

### 10. Discipline & process (everyone)
- The feedback loop (predicted vs actual, self-calibration) plus honest backtests (purged labels, DM
  tests vs honest baselines) — "trust the process, don't chase last week's points".

## What we deliberately did NOT automate
- **Eye test / role analysis** (Ibsen uses both): the dashboard shows the data; the judgment stays yours.
- **Team news confirmation**: pills surface news/doubt status, but the final lineup check before the
  deadline (Friday ~pre-deadline) remains manual — as every elite manager insists.
- **Blindly chasing bandwagons**: the Reddit top-0.1% consensus ("never pick the sub's bandwagon") is
  represented by ownership-aware, EV-driven suggestions rather than popularity sorting.

## Sources
- fantasyfootballfix.com — "5 Tips To Get a Top 10k FPL Finish" (Elite XI: Randazzo, 7× top 10k; Corey Baker)
- allaboutfpl.com — "Interview with World Number 1 FPL Manager – Erik Ibsen (2025/26)"
- premierleague.com — "FPL champion: How to pick your captain and maximise your chips" (Ibsen)
- allaboutfpl.com — "Interview with FPL World Number 1 Manager Over Last 2 Seasons" (Keyuran Govender)
- premierleague.com / theathletic.com — FPL set-piece takers guides; vice-captain.com set-piece edge guide
- reddit.com/r/FantasyPL — "How analytics-driven managers play FPL" (top 0.1%/1% managers)
- fplhints.com — "How to Win at FPL: 15 Strategies (2026/27)"; theathletic.com — expected minutes & rotation
