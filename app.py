#!/usr/bin/env python3
"""FPL Edge — executive dashboard (Streamlit, FFH-style).

Run:  streamlit run app.py --server.port 7860
      (START_DASHBOARD.bat does this for you)

"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from fpl.config import OUTPUTS, load_config, save_config  # noqa: E402
from fpl import odds as ODDS  # noqa: E402
from fpl import optimizer as OPT  # noqa: E402
from fpl import whatif as WI  # noqa: E402

st.set_page_config(page_title="FPL Edge · 2026/27", page_icon=None,
                   layout="wide", initial_sidebar_state="expanded")

BG, CARD, CARD2, LINE = "#0B0F19", "#1E293B", "#16203A", "#243049"
CY, GR, WARN, BAD, GOLD = "#00F2FE", "#10B981", "#F59E0B", "#F43F5E", "#FDE047"
MUT, TXT = "#8CA0BE", "#F8FAFC"
POSC = {"GK": GOLD, "DEF": "#7DD3FC", "MID": GR, "FWD": "#FDA4AF"}
TEAMC = {"ARS": "#EF0107", "AVL": "#95BFE5", "BOU": "#DA291C", "BRE": "#E30613",
         "BHA": "#0057B8", "CHE": "#034694", "COV": "#78D0F3", "CRY": "#1B458F",
         "EVE": "#003399", "FUL": "#64748B", "HUL": "#F5A12D", "IPS": "#3A64A3",
         "LEE": "#FFCD00", "LIV": "#C8102E", "MCI": "#6CABDD", "MUN": "#DA291C",
         "NEW": "#7C8A97", "NFO": "#DD0000", "SUN": "#EB172B", "TOT": "#132257"}

st.markdown(f"""
<style>
  .stApp {{ background: {BG}; color: {TXT}; }}
  section[data-testid="stSidebar"] {{ background: {CARD}; border-right: 1px solid {LINE}; }}
  div[data-testid="stHeader"] {{ background: rgba(11,15,25,.9); border-bottom: 1px solid {LINE}; }}
  .edge-card {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 16px; padding: 18px; margin-bottom: 14px; }}
  .edge-h3 {{ font-size: 11.5px; text-transform: uppercase; letter-spacing: 1.1px; color: {MUT}; margin-bottom: 10px; font-weight: 600;}}
  .edge-kpi {{ background: {CARD2}; border: 1px solid {LINE}; border-radius: 12px; padding: 12px 15px; }}
  .edge-kpi .v {{ font-size: 22px; font-weight: 800; }}
  .edge-kpi .l {{ color: {MUT}; font-size: 11.5px; }}
  .edge-chip {{ background: {CARD2}; border: 1px solid rgba(0,242,254,.28); border-left: 3px solid {CY};
     border-radius: 10px; padding: 9px 12px; font-size: 12.5px; margin: 7px 0; color: #D7E5F7; }}
  .decision {{ background: linear-gradient(135deg, #13233D, #142D35); border: 1px solid rgba(0,242,254,.35);
     border-radius: 16px; padding: 18px; margin-bottom: 12px; }}
  .decision-title {{ color: {CY}; font-size: 11px; letter-spacing: 1.2px; font-weight: 800; text-transform: uppercase; }}
  .decision-main {{ color: {TXT}; font-size: 19px; font-weight: 800; margin: 5px 0; }}
  .decision-note {{ color: {MUT}; font-size: 12.5px; line-height: 1.45; }}
  .edge-pill {{ display:inline-block; padding: 2px 10px; border-radius: 20px; font-size: 10.5px; font-weight: 700; }}
  .p-ok {{ background: rgba(16,185,129,.14); color: {GR}; }}
  .p-risk {{ background: rgba(245,158,11,.14); color: {WARN}; }}
  .p-cy {{ background: rgba(0,242,254,.1); color: {CY}; }}
  .pitch {{ position: relative; border-radius: 14px; overflow: hidden;
     background: repeating-linear-gradient(0deg,#0E4B33 0 36px,#0F5238 36px 72px);
     border: 1px solid #1E6B4A; height: 440px; }}
  .pline {{ position: absolute; border: 1.5px solid rgba(255,255,255,.28); }}
  .pcard {{ position: absolute; width: 92px; transform: translateX(-50%); text-align: center; z-index: 2; }}
  .pdot {{ width: 46px; height: 46px; border-radius: 50%; margin: 0 auto; background: {CARD};
     display:flex; align-items:center; justify-content:center; font-weight: 800; font-size: 11px; position: relative;
     box-shadow: 0 4px 12px rgba(0,0,0,.45); }}
  .pcap {{ position:absolute; top:-7px; right:-9px; background: {GOLD}; color:#1a1a06; font-size:8.5px; font-weight:900; border-radius:6px; padding:1.5px 5px; }}
  .pvice {{ position:absolute; top:-7px; left:-9px; background:#94A3B8; color:#0b0f19; font-size:8.5px; font-weight:900; border-radius:6px; padding:1.5px 5px; }}
  .pnm {{ font-size:10.5px; font-weight:700; margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
     background:rgba(11,15,25,.75); border-radius:6px; padding:1px 4px; }}
  .pfx {{ font-size:9.5px; color:#C7D6EC; background:rgba(11,15,25,.75); border-radius:6px; padding:0 4px; display:inline-block; }}
  .pxp {{ font-size:11px; font-weight:800; color:{CY}; }}
  div[data-testid="stDataFrame"] {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; }}
  div[data-testid="stMetric"] {{ background: {CARD2}; border: 1px solid {LINE}; border-radius: 12px; }}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ data
@st.cache_data(ttl=60)
def load_projections() -> pd.DataFrame:
    files = sorted(OUTPUTS.glob("projections_GW*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.read_parquet(files[-1])


@st.cache_data(ttl=60)
def load_json(name, default=None):
    for base in (OUTPUTS, ROOT / "data/cache"):
        p = base / name
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
    return default


@st.cache_data(ttl=60)
def load_ledger() -> pd.DataFrame:
    """The full-pool predicted-vs-actual ledger (accuracy.py). Empty until a
    finished GW has been scored."""
    p = OUTPUTS / "prediction_ledger.parquet"
    if p.exists():
        try:
            return pd.read_parquet(p)
        except Exception:
            pass
    return pd.DataFrame()


def disp_col(df: pd.DataFrame) -> pd.Series:
    """FFH-style display projection where the pipeline computed it, falling
    back to the honest proj on older projection files."""
    if "display_proj" in df.columns:
        return pd.to_numeric(df["display_proj"], errors="coerce").fillna(
            pd.to_numeric(df.get("proj"), errors="coerce"))
    return pd.to_numeric(df.get("proj"), errors="coerce")


def chart(fig, height=None):
    """Version-safe plotly render (no deprecation warnings on 1.4x-1.6x)."""
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TXT, family="Segoe UI, sans-serif", size=12),
                      margin=dict(l=10, r=10, t=30, b=10), height=height)
    try:
        return st.plotly_chart(fig, width="stretch", key=fig.layout.title.text[:24] if fig.layout.title.text else None)
    except TypeError:
        return st.plotly_chart(fig, use_container_width=True)


def rank_scale(s: pd.Series) -> pd.Series:
    """DISPLAY-ONLY ordering view: maps calibrated xPts onto an 8.5-11
    band by percentile (the commercial-tool look). Not expected points —
    decision math always uses the calibrated values."""
    pct = s.where(s > 0.3).rank(pct=True)
    return (8.5 + 2.5 * pct).fillna(s).round(2)


def sync_team(team_id: int):
    cfg = load_config()
    cfg["team_id"] = int(team_id)
    save_config(cfg)
    import pandas as pd
    from fpl.api import FPL
    from fpl import pipeline
    c = load_config()
    fpl = FPL(c)
    bs = fpl.bootstrap()
    nxt = fpl.next_gw(bs)
    finished = [e["id"] for e in bs["events"] if e.get("finished")]
    pfile = sorted(OUTPUTS.glob("projections_GW*.parquet"))
    if not pfile:
        st.warning("No projections yet — run Update data first.")
        return
    with st.spinner("Fetching your squad and running the solver…"):
        pipeline.analyse_team(c, fpl, bs, pd.read_parquet(pfile[-1]),
                              nxt["id"] if nxt else 1,
                              finished[-1] if finished else 0)
    st.cache_data.clear()


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown(f"<div style='font-weight:800;font-size:19px'>FPL <span style='color:{CY}'>EDGE</span>"
                f"<div style='font-size:10.5px;color:{MUT};letter-spacing:1px'>ELITE ANALYTICS · 26/27</div></div>",
                unsafe_allow_html=True)
    PAGE = st.radio("Navigation", ["Deadline Hub", "My Team & AI Rating", "Transfer Planner & Solver",
                                   "Player Explorer & Risk", "Fixture Ticker & Odds",
                                   "Accuracy Tracker", "Model Diagnostics"],
                    label_visibility="collapsed")
    st.divider()
    cfg0 = load_config()
    tid = st.text_input("FPL team ID", value=str(cfg0.get("team_id") or ""),
                        key="tid_input")
    if st.button("Sync team", use_container_width=True):
        if tid.strip().isdigit():
            sync_team(int(tid))
            st.success("Squad synced")
            st.rerun()
        else:
            st.error("Enter a numeric FPL ID")
    if st.button("Update data", use_container_width=True, type="primary"):
        with st.status("Running weekly pipeline…", expanded=True) as status:
            r = subprocess.run([sys.executable, str(ROOT / "cli.py"), "update"],
                               capture_output=True, text=True,
                               cwd=str(ROOT), timeout=1200)
            st.code(r.stdout[-1500:] if r.stdout else r.stderr[-1500:])
            status.update(label="Done" if r.returncode == 0 else "Failed",
                          state="complete" if r.returncode == 0 else "error")
        st.cache_data.clear()
        st.rerun()
    plan0 = load_json("season_plan.json", {}) or {}
    rep0 = load_json(sorted(OUTPUTS.glob("my_team_GW*.json"))[-1].name,
                     {}) if list(OUTPUTS.glob("my_team_GW*.json")) else {}
    dl = (plan0.get("deadlines") or {}).get(str(plan0.get("next_gw", "")))
    st.caption(f"Gameweek **{plan0.get('next_gw', '–')}**  ·  deadline **{dl[:16].replace('T', ' ') if dl else '–'}**\n\n"
               f"Free transfers **{rep0.get('ft_bank', '–')}**  ·  "
               f"Team value **£{rep0.get('team_value', '–')}m**  ·  "
               f"AI rating **{(rep0.get('ai_rating') or {}).get('overall', '–')}**/100")

PROJ = load_projections()
PLAN = load_json("season_plan.json", {}) or {}
TEAMREP = (load_json(sorted(OUTPUTS.glob("my_team_GW*.json"))[-1].name, {})
           if list(OUTPUTS.glob("my_team_GW*.json")) else {})
MODEL = {"selection": load_json("model_selection.json", {}),
         "report": load_json("backtest_report.json", {}),
         "aux": load_json("aux_model_validation.json", {})}
NEXT_GW = PLAN.get("next_gw")


def deadline_text() -> str:
    """Human-readable deadline state, resilient to an absent/stale plan."""
    raw = (PLAN.get("deadlines") or {}).get(str(NEXT_GW))
    if not raw:
        return "Deadline unavailable"
    try:
        then = pd.Timestamp(raw)
        now = pd.Timestamp.now(tz="UTC")
        delta = then - now
        if delta.total_seconds() <= 0:
            return "Deadline passed — refresh after results settle"
        hrs = int(delta.total_seconds() // 3600)
        return f"{hrs // 24}d {hrs % 24}h to deadline" if hrs >= 24 else f"{hrs}h to deadline"
    except Exception:
        return raw[:16].replace("T", " ") + " UTC"


def captain_call(team: dict) -> dict:
    """Turn a captain table into a decision and an honest confidence label."""
    caps = team.get("captain_table") or []
    if not caps:
        return {"name": "—", "confidence": "No recommendation", "note": "Sync your team first."}
    first = caps[0]
    second = caps[1] if len(caps) > 1 else None
    gap = float(first.get("captain_score", 0) or 0) - float(second.get("captain_score", 0) or 0) if second else 9
    if gap < 0.12:
        confidence = "Coin flip"
        note = f"Only {gap:.2f} captain-score points separate {first.get('name')} and {second.get('name')} — use your risk preference."
    elif gap < 0.35:
        confidence = "Lean, not lock"
        note = f"{first.get('name')} is the safer model choice; the alternative remains live."
    else:
        confidence = "Clear model edge"
        note = f"{first.get('name')} leads by {gap:.2f} captain-score points."
    return {"name": first.get("name", "—"), "confidence": confidence, "note": note,
            "floor": first.get("p_floor"), "ceiling": first.get("p_ceiling"),
            "xpts": first.get("proj")}


def plan_impact(plan: dict, team: dict, players: pd.DataFrame) -> dict:
    """Summarise a transfer plan in manager language: final XI, formation and gain."""
    squad = [int(p["player_id"]) for p in team.get("players", [])]
    before = set(int(p["player_id"]) for p in team.get("xi", []))
    for move in plan.get("moves", []):
        out_id, in_id = move.get("out_id"), move.get("in_id")
        if out_id in squad:
            squad.remove(out_id)
        if in_id is not None:
            squad.append(int(in_id))
    try:
        xi_ids, fmt = OPT.best_xi(squad, players, "proj")
        xi = players[players.player_id.isin(xi_ids)]
        after = set(int(x) for x in xi_ids)
        return {"formation": f"{fmt[0]}-{fmt[1]}-{fmt[2]}",
                "xi_ev": float(xi["proj"].sum() + xi["proj"].max()),
                "enter": ", ".join(xi[~xi.player_id.isin(before)]["name"].tolist()) or "No new starter",
                "leave": ", ".join(p["name"] for p in team.get("xi", [])
                                  if int(p["player_id"]) not in after) or "No starter leaves"}
    except Exception:
        return {"formation": team.get("formation", "—"), "xi_ev": None,
                "enter": "Final XI unavailable", "leave": ""}


def team_alerts(team: dict, players: pd.DataFrame) -> list[str]:
    """Only surface issues that can alter a deadline decision."""
    alerts = []
    player_ids = {int(p["player_id"]) for p in team.get("players", [])}
    if not players.empty and player_ids:
        squad = players[players.player_id.isin(player_ids)]
        risks = squad[(pd.to_numeric(squad.get("xminutes"), errors="coerce").fillna(90) < 60)
                      | (pd.to_numeric(squad.get("chance"), errors="coerce").fillna(100) < 75)]
        if not risks.empty:
            alerts.append("Availability watch: " + ", ".join(risks["name"].head(3).tolist()))
    src = team.get("squad_source") or {}
    if src and not src.get("live", True):
        alerts.append("Your displayed squad is the last deadline-locked team; use What-if for planned moves.")
    plans = team.get("transfer_plans") or []
    if plans and not plans[0].get("moves"):
        alerts.append("Roll recommended: no transfer clears the model's gain threshold.")
    return alerts


# ------------------------------------------------------------------ pitch
def pitch_html(xi: list, scale=None) -> str:
    rows = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in xi:
        rows.setdefault(p["pos"], []).append(p)
    yfor = {"GK": 87, "DEF": 68, "MID": 47, "FWD": 24}
    cards = ""
    for pos in ("GK", "DEF", "MID", "FWD"):
        arr = sorted(rows[pos], key=lambda p: -p.get("proj", 0))
        for i, p in enumerate(arr):
            x = 50 + (i - (len(arr) - 1) / 2) * min(24, 84 / max(len(arr), 1))
            col = TEAMC.get(p.get("team", ""), "#7DD3FC")
            inj = p.get("chance") is not None and p["chance"] < 100
            border = WARN if inj else col
            glow = f"box-shadow:0 0 10px rgba(245,158,11,.55);" if inj else ""
            xp = scale(p) if scale else p.get("proj", 0)
            cards += (f"<div class='pcard' style='left:{x:.1f}%;top:{yfor[pos]}%'>"
                      f"<div class='pdot' style='border:2.5px solid {border};{glow}'>"
                      f"{(p.get('team') or '')[:3]}"
                      + ("<span class='pcap'>C ×2</span>" if p.get("captain") else "")
                      + ("<span class='pvice'>V</span>" if p.get("vice") else "")
                      + "</div>"
                      f"<div class='pnm'>{p['name']}</div>"
                      f"<div class='pfx'>{p.get('opp','')}"
                      + (f" · {p['fdr']}" if p.get("fdr") else "") + "</div>"
                      f"<div class='pxp'>{xp:.1f}" + ("</div>" if scale else " xPts</div>")
                      + "</div>")
    return (f"<div class='pitch'>"
            "<div class='pline' style='left:50%;top:0;bottom:0;width:0'></div>"
            "<div class='pline' style='left:50%;top:50%;width:110px;height:110px;"
            "border-radius:50%;transform:translate(-50%,-50%)'></div>"
            "<div class='pline' style='left:50%;bottom:-8px;width:190px;height:66px;"
            "transform:translateX(-50%)'></div>"
            "<div class='pline' style='left:50%;top:-8px;width:190px;height:66px;"
            "transform:translateX(-50%)'></div>"
            f"{cards}</div>")


def bench_html(bench: list) -> str:
    out = ""
    for b in bench:
        news = f" <span style='color:{WARN}'>· {b['news'][:24]}</span>" if b.get("news") else ""
        out += (f"<div class='edge-kpi' style='min-width:150px'>"
                f"<div class='l'>{b['pos']} · {b.get('team','')} · {b.get('opp','')}</div>"
                f"<div class='v' style='font-size:14px'>{b['name']} "
                f"<span style='color:{CY};font-size:12px'>{b['proj']:.1f}</span></div>"
                f"<div class='l'>{b['xm']:.0f} min{news}</div></div>")
    return f"<div style='display:flex;gap:10px;flex-wrap:wrap;margin-top:12px'>{out}</div>"


def gauge_fig(score: int):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"size": 44, "color": GR if score >= 75 else CY if score >= 50 else WARN}},
        title={"text": "<span style='font-size:11px;letter-spacing:1.5px;color:#8CA0BE'>AI TEAM RATING</span>", "font": {"size": 13}},
        gauge={"axis": {"range": [0, 100], "tickcolor": MUT},
               "bar": {"color": CY, "thickness": 0.16},
               "bgcolor": "rgba(0,0,0,0)",
               "borderwidth": 0,
               "steps": [{"range": [0, 50], "color": "#26314B"},
                         {"range": [50, 75], "color": "#1F3D55"},
                         {"range": [75, 100], "color": "#155E4A"}]}))
    return fig


# ------------------------------------------------------------------ deadline hub
if PAGE == "Deadline Hub":
    if not TEAMREP or TEAMREP.get("error"):
        st.title("Your FPL deadline desk")
        st.info("Enter your FPL team ID in the sidebar, run **Update data**, then press **Sync team**. "
                "This page will turn the model into a start, captain, transfer and risk checklist.")
    else:
        cap = captain_call(TEAMREP)
        plans = TEAMREP.get("transfer_plans") or []
        best = plans[0] if plans else {"moves": [], "gain": 0, "cost": 0, "verdict": "hold"}
        impact = plan_impact(best, TEAMREP, PROJ) if not PROJ.empty else {}
        st.markdown(f"# GW{NEXT_GW or '–'} deadline desk")
        st.caption(f"{deadline_text()} · {TEAMREP.get('ft_bank', '–')} free transfer(s) · "
                   f"£{TEAMREP.get('bank', '–')}m in the bank · {TEAMREP.get('team_name', 'Your team')}")
        a, b, c = st.columns(3, gap="large")
        with a:
            st.markdown(f"<div class='decision'><div class='decision-title'>01 · Captain</div>"
                        f"<div class='decision-main'>{cap['name']}</div>"
                        f"<div class='decision-note'><b>{cap['confidence']}</b> · {cap['note']}<br>"
                        f"xPts {float(cap.get('xpts') or 0):.1f} · floor "
                        f"{100 * float(cap.get('floor') or 0):.0f}% · ceiling "
                        f"{100 * float(cap.get('ceiling') or 0):.0f}%</div></div>",
                        unsafe_allow_html=True)
        with b:
            if best.get("moves"):
                moves = " + ".join(f"{m.get('out')} → {m.get('in')}" for m in best["moves"])
                move_title = moves
                move_note = (f"{str(best.get('verdict', 'plan')).upper()} · "
                             f"+{float(best.get('gain', 0)):.1f} expected points over the horizon · "
                             f"{('−' + str(best.get('cost'))) if best.get('cost') else 'no hit'}")
            else:
                move_title, move_note = "Roll the transfer", "No available move beats holding your free transfer."
            st.markdown(f"<div class='decision'><div class='decision-title'>02 · Transfer</div>"
                        f"<div class='decision-main'>{move_title}</div>"
                        f"<div class='decision-note'>{move_note}<br>{best.get('rationale', '')}</div></div>",
                        unsafe_allow_html=True)
        with c:
            xi_ev = impact.get("xi_ev")
            xi_title = (f"{impact.get('formation', TEAMREP.get('formation', '—'))} · {xi_ev:.1f} xPts"
                        if xi_ev is not None else TEAMREP.get("formation", "—"))
            st.markdown(f"<div class='decision'><div class='decision-title'>03 · Starting XI</div>"
                        f"<div class='decision-main'>{xi_title}</div>"
                        f"<div class='decision-note'>After the plan: <b>{impact.get('enter', '—')}</b> enters; "
                        f"<b>{impact.get('leave', '—')}</b> leaves the XI.</div></div>",
                        unsafe_allow_html=True)

        st.markdown("<div class='edge-card'><div class='edge-h3'>Act before you lock the team</div></div>",
                    unsafe_allow_html=True)
        alerts = team_alerts(TEAMREP, PROJ)
        if alerts:
            for alert in alerts:
                st.markdown(f"<div class='edge-chip' style='border-left-color:{WARN}'>{alert}</div>",
                            unsafe_allow_html=True)
        else:
            st.success("No material availability, squad-freshness or transfer alerts from the latest refresh.")
        next_steps = st.columns(3)
        next_steps[0].metric("Starting XI", TEAMREP.get("formation", "—"),
                             f"{TEAMREP.get('xi_proj', '—')} incl. captain", border=True)
        next_steps[1].metric("Bench", f"{TEAMREP.get('bench_proj', '—')} xPts",
                             "Review first-sub order", border=True)
        next_steps[2].metric("Team rating", f"{(TEAMREP.get('ai_rating') or {}).get('overall', '—')}/100",
                             "See drivers on My Team", border=True)
        st.caption("Use Transfer Planner to compare alternatives, Player Explorer to research targets, "
                   "and My Team to run pre-deadline What-if moves. FPL transfers are never submitted by this app.")

# ------------------------------------------------------------------ page 1
elif PAGE == "My Team & AI Rating":
    if not TEAMREP or TEAMREP.get("error"):
        st.info("Enter your FPL team ID in the sidebar and press **Sync team** "
                "(requires one Update data run first).")
    else:
        rt = TEAMREP.get("ai_rating") or {}
        c1, c2 = st.columns([1, 2.1], gap="large")
        with c1:
            st.markdown("<div class='edge-card'><div class='edge-h3'>AI team rating</div>"
                        "<div id='gauge'></div></div>", unsafe_allow_html=True)
            chart(gauge_fig(rt.get("overall", 0)), height=250)
            st.markdown(
                f"<div class='edge-card' style='padding:12px 16px'>"
                f"<div style='font-size:11.5px;color:{MUT}'>Attack <b style='color:{TXT}'>{rt.get('attack')}</b> · "
                f"Availability <b style='color:{TXT}'>{rt.get('availability')}</b> · "
                f"Fixtures <b style='color:{TXT}'>{rt.get('fixtures')}</b></div>"
                f"<div style='font-size:11.5px;color:{MUT};margin-top:6px'>XI xPts "
                f"<b style='color:{TXT}'>{rt.get('xi_ev')}</b> vs league-optimal "
                f"<b style='color:{TXT}'>{rt.get('league_best_xi')}</b></div></div>",
                unsafe_allow_html=True)
        with c2:
            RANKP = str(st.session_state.get("scale_mode", "")).startswith("FFH")
            pitch_scale = None
            if RANKP and not PROJ.empty:
                _scaled = disp_col(PROJ)
                _scaled.index = PROJ["player_id"]
                pitch_scale = lambda pl: float(_scaled.get(pl.get("player_id"),
                                                                pl.get("proj", 0)))
            st.markdown(f"<div class='edge-card'><div class='edge-h3'>Starting XI — "
                        f"GW{NEXT_GW} (formation {TEAMREP.get('formation')})</div>"
                        f"{pitch_html(TEAMREP.get('xi') or [], scale=pitch_scale)}"
                        f"{bench_html([p for p in TEAMREP.get('players', []) if not p['in_xi']])}</div>"
                        + ("<div class='edge-pill p-risk' style='margin-top:6px'>FFH RANKING — "
                           "ceiling-weighted display, not expected points</div>" if RANKP else ""),
                        unsafe_allow_html=True)
        m = st.columns(4)
        vc = TEAMREP.get("value_change")
        vcs = f"{'+' if (vc or 0) >= 0 else ''}{vc} vs last GW" if vc is not None else "—"
        m[0].metric("Team value", f"£{TEAMREP.get('team_value')}m", vcs,
                    border=True)
        m[1].metric("Free transfers", TEAMREP.get("ft_bank"), "−4 per hit", border=True)
        m[2].metric("Captain (SAFE)", TEAMREP.get("recommended_captain") or "—",
                    f"you: {TEAMREP.get('current_captain') or '—'}", border=True)
        m[3].metric("Overall", f"{TEAMREP.get('total_points', '—')} pts",
                    f"OR {(TEAMREP.get('overall_rank') or 0)/1e6:.2f}M" if TEAMREP.get("overall_rank") else "—",
                    border=True)
        st.markdown("<div class='edge-card'><div class='edge-h3'>Structure &amp; next moves</div>"
                    + "".join(f"<span class='edge-pill p-cy'>{f}</span> "
                              for f in (TEAMREP.get("structure", {}).get("flags") or []))
                    + "".join(f"<div class='edge-chip'><b>[{p.get('verdict','').upper()}]</b> "
                              f"{p.get('rationale','')}</div>"
                              for p in (TEAMREP.get("transfer_plans") or [])[:2])
                    + "</div>", unsafe_allow_html=True)
        st.caption("Full solver and captaincy analysis on the Transfer Planner tab.")

        # ---- squad freshness banner ----
        srcinfo = TEAMREP.get("squad_source") or {}
        if srcinfo and not srcinfo.get("live", True):
            st.markdown(f"<div class='edge-chip' style='border-left-color:{WARN}'>"
                        f"<b>GW{srcinfo.get('event')} squad — deadline-locked.</b> "
                        f"{srcinfo.get('note', '')}</div>", unsafe_allow_html=True)

        # ---- what-if transfer planner ----
        st.markdown("<div class='edge-card'><div class='edge-h3'>What-if transfer planner "
                    "— model saved or potential transfers before you commit</div>"
                    "<div style='font-size:12px;color:#8CA0BE;margin-bottom:10px'>"
                    "Pre-deadline the public API can't show your saved transfers — model them here. "
                    "Same-position, budget, club-limit and pundit filters applied. Actual transfers "
                    "happen on fantasy.premierleague.com.</div></div>", unsafe_allow_html=True)
        squad_ids_wi = [int(p["player_id"]) for p in TEAMREP.get("players", [])]
        if "wi" not in st.session_state:
            st.session_state.wi = {}
        bank_wi = float(TEAMREP.get("bank", 0) or 0) * 10
        cols3 = st.columns(3)
        for i, pl in enumerate(TEAMREP.get("players", [])):
            with cols3[i % 3]:
                a, b = st.columns([1.05, 1.5])
                a.markdown(f"**{pl['name']}**<br><span style='color:{MUT};font-size:11px'>"
                           f"{pl['pos']} · £{pl.get('price', 0):.1f}m · {pl['proj']:.1f}</span>",
                           unsafe_allow_html=True)
                cands = WI.candidates(PROJ, squad_ids_wi, int(pl["player_id"]), bank=bank_wi)
                labels = ["— keep —"] + [f"{r['name']} · £{r['value']/10:.1f}m · {r['proj']:.1f}"
                                         for _, r in cands.iterrows()]
                pick = b.selectbox("replace", labels, key=f"wi_{pl['player_id']}",
                                   label_visibility="collapsed")
                if pick != "— keep —":
                    st.session_state.wi[int(pl["player_id"])] = int(
                        cands.iloc[labels.index(pick) - 1]["player_id"])
                else:
                    st.session_state.wi.pop(int(pl["player_id"]), None)
        bb1, bb2, bb3 = st.columns([1, 1, 3])
        if bb1.button("Apply what-if", type="primary"):
            swaps = [{"out": o, "in": n} for o, n in st.session_state.wi.items()]
            st.session_state.wi_result = WI.evaluate(
                PROJ, squad_ids_wi, swaps, bank=bank_wi,
                ft_bank=int(TEAMREP.get("ft_bank", 1)),
                league_best_xi=rt.get("league_best_xi"))
        if bb2.button("Reset"):
            st.session_state.wi = {}
            st.session_state.pop("wi_result", None)
        if not st.session_state.wi and "wi_result" not in st.session_state:
            bb3.caption("Pick replacements above (e.g. your saved GW2 transfers), then Apply.")

        wir = st.session_state.get("wi_result")
        if wir:
            if not wir.get("ok"):
                st.error(f"What-if rejected: {wir.get('error')}")
            else:
                for rj in wir.get("rejected", []):
                    st.warning(f"Rejected swap {rj.get('out')}→{rj.get('in')}: {rj.get('reason')}")
                dm = st.columns(6)
                dm[0].metric("Δ XI EV (incl. hits)", f"{wir['delta_xi_ev']:+}",
                             f"{wir['hits']} hit(s)", border=True,
                             delta_color="normal" if wir["delta_xi_ev"] >= 0 else "inverse")
                dm[1].metric("Δ 5-GW horizon", f"{wir['delta_horizon']:+}", border=True)
                dm[2].metric("Bank after", f"£{wir['bank_after']}m", border=True)
                dm[3].metric("New formation", wir["formation"], border=True)
                dm[4].metric("New captain", wir["recommended_captain"] or "—", border=True)
                dm[5].metric("AI rating", wir["ai_rating"],
                             f"{wir['ai_rating'] - rt.get('overall', 0):+d}", border=True)
                wi_xi = [dict(p) for p in wir["players"] if p["in_xi"]]
                orig_caps = {int(q["player_id"]) for q in TEAMREP.get("players", [])
                             if q.get("captain")}
                for p in wi_xi:
                    p["captain"] = int(p["player_id"]) in orig_caps
                st.markdown(f"<div class='edge-card' style='margin-top:10px'><div class='edge-h3'>"
                            f"Modeled XI — {wir['formation']} · "
                            f"{wir['xi_ev']} xPts (captain incl.)</div>"
                            f"{pitch_html(wi_xi)}</div>", unsafe_allow_html=True)
                st.caption("Captain badge on the modeled pitch follows your current armband if "
                           "still in the squad; the solver's pick is shown in New captain.")

# ------------------------------------------------------------------ page 2
elif PAGE == "Transfer Planner & Solver":
    if not TEAMREP:
        st.info("Sync your team first.")
    else:
        left, right = st.columns([1.35, 1], gap="large")
        with left:
            st.markdown("<div class='edge-card'><div class='edge-h3'>Five-gameweek projection grid — your squad</div>"
                        "</div>", unsafe_allow_html=True)
            gws = None
            rows = []
            for p in sorted(TEAMREP.get("players", []), key=lambda x: -x["proj"]):
                gws = p.get("gws") or []
                rows.append({"Player": p["name"] + (" (C)" if p.get("captain") else ""),
                             "Pos": p["pos"], "Club": p.get("team", ""),
                             **{f"GW{NEXT_GW + i}": v for i, v in enumerate(gws)},
                             "5-GW": round(sum(v for v in gws if v), 1),
                             "XI": "yes" if p["in_xi"] else "bench"})
            st.dataframe(pd.DataFrame(rows), hide_index=True, height=430)
        with right:
            st.markdown("<div class='edge-card'><div class='edge-h3'>Solver plans — MILP over budget, FT bank, hits, ≤3/club</div>"
                        "</div>", unsafe_allow_html=True)
            if st.button("Suggest best transfers", type="primary", use_container_width=True):
                if st.session_state.get("tid_input", "").strip().isdigit():
                    sync_team(int(st.session_state["tid_input"]))
                    st.session_state["solver_ran"] = True
                    st.rerun()
            st.caption(f"bank £{TEAMREP.get('bank')}m · {TEAMREP.get('ft_bank')} FT · "
                       "plans scored on 5-GW horizon EV")
            for p in (TEAMREP.get("transfer_plans") or [])[:5]:
                moves = " · ".join(f"**{m['out']}** → **{m['in']}** (£{m['price']}m, "
                                   f"GW {m['in_proj']})" for m in p["moves"]) or "hold"
                st.markdown(f"<div class='edge-chip'><b>[{p['verdict'].upper()} · "
                            f"{'FREE' if not p['cost'] else '−' + str(p['cost'])}]</b> "
                            f"{moves} — <b>+{p['gain']} EV</b><br>{p.get('rationale','')}</div>",
                            unsafe_allow_html=True)
        st.markdown("<div class='edge-card'><div class='edge-h3'>Captaincy — floor &amp; ceiling</div></div>",
                    unsafe_allow_html=True)
        caps = pd.DataFrame([{"Player": c["name"], "Pos": c["position"], "Club": c["team_short"],
                              "xPts": c["proj"], "CapScore": round(c.get("captain_score", c["proj"]), 2),
                              "Floor %": round(100 * c["p_floor"]) if c.get("p_floor") is not None else None,
                              "Ceil %": round(100 * c["p_ceiling"]) if c.get("p_ceiling") is not None else None,
                              "xMin": c["xminutes"], "Nailed": c.get("nailed"),
                              "SP": "P" if c.get("pens", 0) >= 1 else "", "Own %": c["selected_by"],
                              "Tag": c.get("tag", "")}
                             for c in (TEAMREP.get("captain_table") or [])])
        st.dataframe(caps, hide_index=True)
        st.caption("Floor = P(≥2 pts) · Ceil = P(≥8 pts). SAFE = floor-first captaincy; CEIL = boom probability.")

# ------------------------------------------------------------------ page 3
elif PAGE == "Player Explorer & Risk":
    if PROJ.empty:
        st.info("Run Update data first.")
    else:
        st.markdown("<div class='edge-card'><div class='edge-h3'>Risk quadrant — effective ownership vs projected points</div></div>",
                    unsafe_allow_html=True)
        scale_mode = st.radio(
            "Projection display scale",
            ["FFH ranking (ceiling-weighted)", "Calibrated xPts (expected points)"],
            horizontal=True, label_visibility="collapsed", key="scale_mode",
            help="FFH ranking is a display-only, ceiling-weighted view (mostly "
                 "the multi-GW horizon rate + upside) so premium attackers sit "
                 "on top the way commercial tools present them. Calibrated xPts "
                 "is the honest single-GW expected points. Either way, every "
                 "decision (best XI, captain, transfers) uses the calibrated "
                 "values underneath — the toggle only changes what you see.")
        RANK = scale_mode.startswith("FFH")
        d = PROJ[PROJ.proj > 0.3].copy()
        d["EO%"] = (100 * d.eo.fillna(0)).clip(lower=0.05)
        d["xPts"] = disp_col(d) if RANK else d.proj
        eo_med = d["EO%"].median()
        x_med = d.xPts.median()
        fig = px.scatter(d, x="EO%", y="xPts", color="position",
                         color_discrete_map=POSC, hover_name="name",
                         hover_data={"team_short": True, "proj_3gw": ":.1f",
                                     "risk_flag": True, "EO%": ":.1f", "xPts": ":.1f",
                                     "position": False},
                         size=d.xPts.clip(0.4), size_max=11, opacity=0.82)
        fig.add_hline(y=x_med, line=dict(color=LINE, dash="dash"))
        fig.add_vline(x=eo_med, line=dict(color=LINE, dash="dash"))
        for x, y, t in [(0.02, d.xPts.max(), "EXPLOSIVE DIFFERENTIALS"),
                        (eo_med * 1.15, d.xPts.max(), "RANK PROTECTORS"),
                        (0.02, d.xPts.min() + .1, "DEEP DIFFERENTIALS"),
                        (eo_med * 1.15, d.xPts.min() + .1, "TEMPLATE TRAPS")]:
            fig.add_annotation(x=x, y=y, text=t, showarrow=False,
                               font=dict(size=9.5, color=MUT))
        fig.update_layout(xaxis=dict(gridcolor=LINE, title="effective ownership %"),
                          yaxis=dict(gridcolor=LINE,
                                     title="FFH ranking (display)" if RANK else "xPts"),
                          showlegend=True, legend=dict(bgcolor="rgba(0,0,0,0)"))
        chart(fig, height=420)

        # select a player -> profile modal
        st.markdown("<div class='edge-card'><div class='edge-h3'>Players — select a row to open the profile</div></div>",
                    unsafe_allow_html=True)
        tbl = d.copy()
        tbl["name_low"] = tbl.name.str.lower()
        qc = st.columns([2, 1, 1, 1])
        q = qc[0].text_input("Search", placeholder="player name", key="pq").lower()
        pos = qc[1].selectbox("Position", ["", "GK", "DEF", "MID", "FWD"])
        maxp = qc[2].selectbox("Max price", [200, 45, 55, 65, 80, 100],
                               format_func=lambda v: "any" if v == 200 else f"≤£{v/10:.1f}m")
        nsel = qc[3].selectbox("Show", [10, 25, 999], format_func=lambda v: "all" if v == 999 else str(v))
        view = tbl[(tbl.name_low.str.contains(q or "")) & (tbl.position.str.contains(pos))
                   & (tbl.value / 10 <= maxp)].nlargest(nsel, "xPts")
        view = view.rename(columns={"team_short": "Club", "opp_label": "Next", "value": "£(x10)",
                                    "proj_3gw": "3-GW", "sd": "SD", "eo": "EO",
                                    "risk_flag": "Risk", "xminutes": "xMin", "nailed": "Nailed"})
        if RANK:
            view = view.rename(columns={"xPts": "FFH pts"})
        disp_cols = ["name", "position", "Club", "Next", "£(x10)",
                     "FFH pts" if RANK else "xPts", "3-GW",
                     "SD", "EO", "Risk", "xMin", "Nailed"]
        event = st.dataframe(view[disp_cols],
                             hide_index=True, on_select="rerun", selection_mode="single-row",
                             key="explore_sel", height=380)
        sel = event.selection.rows if hasattr(event, "selection") else []
        short = load_json("shortlist.json", {"ids": []}) or {"ids": []}
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Shortlist", f"{len(short.get('ids', []))} targets", border=True)
        sc2.metric("Combined cost", f"£{PROJ[PROJ.player_id.isin(short.get('ids', []))].value.sum()/10:.1f}m", border=True)
        sc3.metric("Combined xPts", f"{PROJ[PROJ.player_id.isin(short.get('ids', []))].proj.sum():.1f}", border=True)

        if sel:
            pid = int(view.iloc[sel[0]].player_id)
            row = PROJ[PROJ.player_id == pid].iloc[0]

            @st.dialog("Player profile", width="large")
            def profile():
                gws = {c.replace("proj_gw", "GW"): round(float(row[c]), 1)
                       for c in PROJ.columns if c.startswith("proj_gw") and pd.notna(row[c])}
                t1, t2, t3, t4 = st.columns(4)
                t1.metric("xPts", f"{row.proj:.2f}")
                t2.metric("xMin", f"{row.xminutes:.0f}")
                t3.metric("SD", f"±{row.sd:.2f}")
                t4.metric("EO", f"{100*row.eo:.1f}%")
                figb = go.Figure(go.Bar(x=list(gws), y=list(gws.values()),
                                        marker_color=CY, text=[f"{v:.1f}" for v in gws.values()],
                                        textposition="outside"))
                figb.update_layout(title="Per-GW projections", yaxis=dict(gridcolor=LINE))
                chart(figb, height=240)
                mm = st.columns(4)
                mm[0].metric("Floor P(≥2)", f"{100*row.p_floor:.0f}%")
                mm[1].metric("Ceil P(≥8)", f"{100*row.p_ceiling:.0f}%")
                mm[2].metric("P(start)", f"{100*row.p_start:.0f}%")
                mm[3].metric("Nailed", f"{row.nailed:.0f}")
                st.caption(f"{row.position} · {row.team_short} · £{row.value/10:.1f}m · "
                           f"vs {row.opp_label} (FDR {row.fdr:.0f}) · risk: {row.risk_flag} · "
                           f"{'penalty taker' if row.pens >= 1 else 'no pens'} · "
                           f"price signal: {'rise' if (row.price_like or 0) >= 1 else 'fall' if (row.price_like or 0) <= -2 else 'flat'}")
                ids = set(short.get("ids", []))
                led = load_ledger()
                if not led.empty and pid in set(led.player_id):
                    h = led[led.player_id == pid].sort_values("gw")
                    figh = go.Figure()
                    figh.add_trace(go.Bar(
                        x=[f"GW{int(g)}" for g in h.gw], y=h.actual,
                        name="actual", marker_color=GR))
                    figh.add_trace(go.Scatter(
                        x=[f"GW{int(g)}" for g in h.gw], y=h.proj,
                        name="projected", mode="lines+markers",
                        line=dict(color=CY, width=2)))
                    figh.update_layout(title="Projected vs actual — past GWs",
                                       yaxis=dict(gridcolor=LINE),
                                       legend=dict(orientation="h", bgcolor="rgba(0,0,0,0)"))
                    chart(figh, height=230)
                    hp = pd.to_numeric(h.proj, errors="coerce")
                    ha = pd.to_numeric(h.actual, errors="coerce")
                    mae_p = float((hp - ha).abs().mean())
                    st.caption(f"Season so far: {len(h)} GW(s) scored · "
                               f"mean proj {hp.mean():.1f} vs mean actual "
                               f"{ha.mean():.1f} · MAE {mae_p:.2f}")
                if st.button("Remove from shortlist" if pid in ids else "Add to shortlist"):
                    (ids.remove if pid in ids else ids.add)(pid)
                    (OUTPUTS / "shortlist.json").write_text(json.dumps({"ids": sorted(ids)}))
                    st.cache_data.clear()
                    st.rerun()

            profile()

# ------------------------------------------------------------------ page 4
elif PAGE == "Fixture Ticker & Odds":
    grid = (PLAN.get("grid") or {}).get("grid") or {}
    if not grid:
        st.info("Run Update data to generate the season plan.")
    else:
        st.markdown("<div class='edge-card'><div class='edge-h3'>Fixture ticker — official FDR</div></div>",
                    unsafe_allow_html=True)
        teams = sorted(grid)
        gws = [c["gw"] for c in grid[teams[0]]]
        z, txt = [], []
        for t in teams:
            z.append([(-1 if c["n"] == 0 else c["diff"]) for c in grid[t]])
            txt.append([("—" if c["n"] == 0 else " / ".join(c["opp"])) for c in grid[t]])
        fig = go.Figure(go.Heatmap(
            z=z, x=[f"GW{g}" for g in gws], y=teams, text=txt, texttemplate="%{text}",
            textfont=dict(size=9), showscale=False,
            colorscale=[[0.0, "#1a2436"], [0.01, "#123524"], [0.35, "#1c4531"],
                        [0.65, "#4a3a14"], [1.0, "#57201f"]],
            zmin=-1, zmax=10, xgap=2, ygap=2, hovertemplate="%{y} %{x}<br>%{text}<extra></extra>"))
        fig.update_layout(yaxis=dict(autorange="reversed"), height=560)
        chart(fig)
        dgw = PLAN.get("dgw_bgw") or {}
        a, b = st.columns(2)
        a.markdown(f"<div class='edge-card'><div class='edge-h3'>Double gameweeks</div>"
                   + ("<br>".join(f"GW{d['gw']}: {', '.join(d['teams'])}" for d in dgw.get("dgws", []))
                      or "none scheduled yet") + "</div>", unsafe_allow_html=True)
        b.markdown(f"<div class='edge-card'><div class='edge-h3'>Blank gameweeks</div>"
                   + ("<br>".join(f"GW{d['gw']} ({d['missing']} teams blank)" for d in dgw.get("bgws", []))
                      or "none") + "</div>", unsafe_allow_html=True)
        st.markdown("<div class='edge-card'><div class='edge-h3'>Chip strategy — each chip ×2 in 26/27</div>"
                    + "".join(f"<div class='edge-chip'><b>{c['chip']} ×{c.get('times_left', c.get('times'))}</b> — "
                              f"{c['advice']}</div>" for c in (PLAN.get("chips") or []))
                    + "</div>", unsafe_allow_html=True)
        st.markdown("<div class='edge-card'><div class='edge-h3'>Bookmaker odds</div>", unsafe_allow_html=True)
        odds = ODDS.odds_features()
        if odds:
            st.dataframe(pd.DataFrame(odds).T.rename(columns={
                "lambda_for": "implied goals for", "lambda_ag": "implied goals against",
                "cs": "implied CS%"}), height=320)
        else:
            st.caption("No odds loaded. Add **data/odds.json** (format in src/fpl/odds.py) or set "
                       "**ODDS_API_KEY** — implied clean-sheet % and goal totals then replace static "
                       "FDR in the model automatically.")

# ------------------------------------------------------------------ page 5
elif PAGE == "Accuracy Tracker":
    acc = load_json("accuracy_history.json", {}) or {}
    bias = load_json("inseason_bias.json", {}) or {}
    fb = load_json("feedback_log.json", {}) or {}
    per_gw = acc.get("per_gw") or []
    if not per_gw:
        st.info("No scored gameweeks yet. The accuracy tracker fills in after "
                "the **first finished gameweek** has been scored against its "
                "saved projections — run **Update data** once a GW completes. "
                "It then sharpens every week as more of the same players "
                "accumulate a track record.")
    else:
        cum = acc.get("cumulative") or {}
        k = st.columns(4)
        k[0].metric("GWs scored", acc.get("n_gws", 0), border=True)
        k[1].metric("Season MAE", cum.get("mae", "—"),
                    help="Mean absolute error, projected vs actual, players who "
                         "featured. Lower is better.", border=True)
        k[2].metric("Rank corr (Spearman)", cum.get("spearman", "—"),
                    help="How well the projection ordering matches reality.",
                    border=True)
        cap_hits = [r.get("top_pick_hit") for r in per_gw
                    if r.get("top_pick_hit") is not None]
        cap_rate = round(100 * sum(cap_hits) / len(cap_hits)) if cap_hits else None
        k[3].metric("Top-pick in real top 3", f"{cap_rate}%" if cap_rate is not None else "—",
                    help="How often the single highest projected player landed in "
                         "that GW's actual top 3.", border=True)

        pg = pd.DataFrame(per_gw).sort_values("gw")
        # ---- accuracy trend + the sharpening story ----
        st.markdown("<div class='edge-card'><div class='edge-h3'>Accuracy over the "
                    "season — does it sharpen as data accumulates?</div></div>",
                    unsafe_allow_html=True)
        tcol = st.columns(2)
        with tcol[0]:
            figm = go.Figure()
            figm.add_trace(go.Scatter(x=pg.gw, y=pg.mae, mode="lines+markers",
                                      name="MAE", line=dict(color=CY, width=2)))
            if "rmse" in pg.columns:
                figm.add_trace(go.Scatter(x=pg.gw, y=pg.rmse, mode="lines+markers",
                                          name="RMSE", line=dict(color=WARN, width=1.5, dash="dot")))
            figm.update_layout(title="Per-GW error (lower = sharper)",
                               xaxis=dict(title="GW", gridcolor=LINE),
                               yaxis=dict(gridcolor=LINE),
                               legend=dict(orientation="h", bgcolor="rgba(0,0,0,0)"))
            chart(figm, height=260)
        with tcol[1]:
            figs = go.Figure()
            figs.add_trace(go.Scatter(x=pg.gw, y=pg.spearman, mode="lines+markers",
                                      name="Spearman", line=dict(color=GR, width=2)))
            figs.add_trace(go.Scatter(x=pg.gw, y=pg.bias, mode="lines+markers",
                                      name="bias (proj−actual)", line=dict(color=GOLD, width=1.5)))
            figs.add_hline(y=0, line=dict(color=LINE, dash="dash"))
            figs.update_layout(title="Rank correlation & bias",
                               xaxis=dict(title="GW", gridcolor=LINE),
                               yaxis=dict(gridcolor=LINE),
                               legend=dict(orientation="h", bgcolor="rgba(0,0,0,0)"))
            chart(figs, height=260)
        # ACCURACY_PAGE_BODY_2
        # ---- per-position bias correction (the adaptive mechanism) ----
        st.markdown("<div class='edge-card'><div class='edge-h3'>Adaptive per-position "
                    "correction — the factor applied to next week's projections</div>"
                    "<div style='font-size:12px;color:#8CA0BE;margin-bottom:8px'>"
                    "Learned from the whole player pool, shrunk by sample size and "
                    "recency-weighted. &gt;1 lifts a position the model under-rated; "
                    "&lt;1 trims one it over-rated. It stays near 1.0 early and moves "
                    "more as the same players accumulate gameweeks — this is what "
                    "tightens accuracy through the season.</div></div>",
                    unsafe_allow_html=True)
        factors = (bias.get("factors") or {}) if bias else {}
        perpos = acc.get("per_position") or {}
        bcol = st.columns([1.2, 1])
        with bcol[0]:
            order = ["GK", "DEF", "MID", "FWD"]
            fv = [factors.get(p, 1.0) for p in order]
            figb = go.Figure(go.Bar(
                x=order, y=fv, marker_color=[POSC[p] for p in order],
                text=[f"×{v:.3f}" for v in fv], textposition="outside"))
            figb.add_hline(y=1.0, line=dict(color=MUT, dash="dash"))
            figb.update_layout(title="Applied bias factor by position",
                               yaxis=dict(gridcolor=LINE, range=[0.75, 1.32]))
            chart(figb, height=260)
        with bcol[1]:
            prows = []
            for p in order:
                pp = perpos.get(p) or {}
                prows.append({"Pos": p, "Factor": round(factors.get(p, 1.0), 3),
                              "MAE": pp.get("mae"), "Bias": pp.get("bias"),
                              "n": pp.get("n")})
            st.dataframe(pd.DataFrame(prows), hide_index=True, height=200)
            st.caption(f"From {bias.get('n', 0)} scored player-GWs over "
                       f"{bias.get('n_gws', 0)} GW(s). Updated {bias.get('updated', '—')}.")
        # ACCURACY_PAGE_BODY_3
        # ---- reliability curve + predicted-vs-actual cloud ----
        rcol = st.columns(2)
        rel = acc.get("reliability") or []
        with rcol[0]:
            st.markdown("<div class='edge-card'><div class='edge-h3'>Reliability — "
                        "do projections mean what they say?</div></div>",
                        unsafe_allow_html=True)
            if rel:
                rdf = pd.DataFrame(rel)
                figr = go.Figure()
                lim = max(rdf.pred_mean.max(), rdf.actual_mean.max()) + 0.5
                figr.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines",
                                          line=dict(color=MUT, dash="dash"),
                                          name="perfect"))
                figr.add_trace(go.Scatter(
                    x=rdf.pred_mean, y=rdf.actual_mean, mode="markers+text",
                    marker=dict(size=(rdf.n.clip(1) ** 0.5).clip(6, 26), color=CY),
                    text=rdf.bucket, textposition="top center",
                    name="buckets"))
                figr.update_layout(xaxis=dict(title="projected (bucket mean)", gridcolor=LINE),
                                   yaxis=dict(title="actual (bucket mean)", gridcolor=LINE),
                                   showlegend=False)
                chart(figr, height=280)
                st.caption("Points on the dashed line = well-calibrated. Above it = "
                           "under-projected; below = over-projected.")
            else:
                st.caption("Reliability curve appears once enough GWs are scored.")
        with rcol[1]:
            st.markdown("<div class='edge-card'><div class='edge-h3'>Predicted vs actual "
                        "— every scored player-GW</div></div>", unsafe_allow_html=True)
            led = load_ledger()
            if not led.empty:
                lp = led.copy()
                lp["proj"] = pd.to_numeric(lp.proj, errors="coerce")
                lp["actual"] = pd.to_numeric(lp.actual, errors="coerce")
                lp = lp[pd.to_numeric(lp.get("minutes"), errors="coerce").fillna(0) >= 1]
                lp = lp.dropna(subset=["proj", "actual"])
                lim = max(lp.proj.max(), lp.actual.max()) + 1
                figc = px.scatter(lp, x="proj", y="actual", color="position",
                                  color_discrete_map=POSC, hover_name="name",
                                  opacity=0.5, hover_data={"gw": True, "position": False})
                figc.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines",
                                          line=dict(color=MUT, dash="dash"),
                                          showlegend=False))
                figc.update_layout(xaxis=dict(title="projected", gridcolor=LINE),
                                   yaxis=dict(title="actual", gridcolor=LINE),
                                   legend=dict(orientation="h", bgcolor="rgba(0,0,0,0)"))
                chart(figc, height=280)
            else:
                st.caption("Scatter appears once the ledger has scored rows.")

        # ---- your team's calibration feedback ----
        # feedback_log.json is keyed by GW string: {"1": {gw, predicted, actual,
        # ratio, detail:[...]}, ...}
        if isinstance(fb, dict) and "events" in fb:
            events = fb.get("events") or []
        elif isinstance(fb, dict):
            events = [v for v in fb.values() if isinstance(v, dict)]
        else:
            events = fb or []
        if events:
            st.markdown("<div class='edge-card'><div class='edge-h3'>Your squad — "
                        "predicted vs actual points (personal calibration)</div></div>",
                        unsafe_allow_html=True)
            fdf = pd.DataFrame(events)
            gwc = "gw" if "gw" in fdf.columns else ("event" if "event" in fdf.columns else None)
            pc = next((c for c in ("predicted", "pred", "proj") if c in fdf.columns), None)
            ac = next((c for c in ("actual", "points", "actual_points") if c in fdf.columns), None)
            if gwc and pc and ac:
                fdf = fdf.sort_values(gwc)
                figf = go.Figure()
                figf.add_trace(go.Bar(x=fdf[gwc], y=fdf[ac], name="actual", marker_color=GR))
                figf.add_trace(go.Scatter(x=fdf[gwc], y=fdf[pc], name="predicted",
                                          mode="lines+markers", line=dict(color=CY, width=2)))
                figf.update_layout(xaxis=dict(title="GW", gridcolor=LINE),
                                   yaxis=dict(gridcolor=LINE),
                                   legend=dict(orientation="h", bgcolor="rgba(0,0,0,0)"))
                chart(figf, height=240)
            else:
                st.dataframe(fdf, hide_index=True, height=200)
        st.caption("Projections are scored out-of-sample: each GW's numbers were "
                   "written and saved before that GW kicked off, then compared here "
                   "to what actually happened — no hindsight.")

# ------------------------------------------------------------------ page 6
else:
    rep = MODEL["report"] or {}
    summ = rep.get("summary") or {}
    st.markdown("<div class='edge-card'><div class='edge-h3'>Out-of-sample validation — "
                "2025/26, expanding window, purged labels</div></div>", unsafe_allow_html=True)
    rows = []
    names = {"p_blend": "Blend (live)", "p_poisson": "Poisson 1-GW", "p_hurdle": "Hurdle 1-GW",
             "p_xp": "vaastav xP", "p_form": "Naive form", "p_3gw": "Tweedie 3-GW"}
    for k, n in names.items():
        if k in summ:
            rows.append({"Model": n, "MAE": summ[k].get("MAE"), "Spearman": summ[k].get("Spearman"),
                         "Captain top-3 %": (round(100 * summ[k]["cap_hit3"]) if summ[k].get("cap_hit3") is not None else None),
                         "Calibrated MAE": summ[k].get("MAE_calibrated")})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    aux = MODEL.get("aux") or {}
    if aux:
        st.caption(f"Availability models — P(start) AUC {aux.get('start_AUC')} · P(60+) "
                   f"{aux.get('min60_AUC')} · haul {aux.get('haul_AUC')} · blank "
                   f"{aux.get('blank_AUC')} · minutes MAE {aux.get('minutes_MAE')}.")
    dm = rep.get("dm_vs_xp") or {}
    if dm:
        st.caption("Diebold-Mariano vs vaastav xP (valid rows): "
                   + " · ".join(f"{k}: t={v.get('t')}" for k, v in dm.items() if isinstance(v, dict)))
    st.markdown(f"<div class='edge-card'><div class='edge-h3'>Engineering notes</div>"
                f"<div style='font-size:12.5px;line-height:1.8;color:#D7E5F7'>"
                "xPts = calibrated poisson+hurdle blend (per-position isotonic), certainty-blended with "
                "xMins/90 × learned pts/90, soft-capped at 11 — no unscaled 16–17 xPts outputs.<br>"
                "ETL validated every run (100% id/club/position match vs bootstrap-static).<br>"
                "Effective ownership & SD drive the risk quadrant; chips, MILP solver and pundit "
                "filters run under 2026/27 rules.<br>"
                "Odds integration is an explicit hook (data/odds.json or ODDS_API_KEY) with FDR fallback."
                "</div></div>", unsafe_allow_html=True)
