#!/usr/bin/env python3
"""FPL Edge — command line interface.

Most things you'll do in the dashboard (START_DASHBOARD.bat), but every
command is available here too:

  python cli.py setup      one-time: download history, train, project
  python cli.py update     the weekly refresh (data + retrain + analysis)
  python cli.py backtest   re-run the leakage-free validation
  python cli.py serve      start the dashboard
  python cli.py status     show what's in outputs/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fpl.config import OUTPUTS, load_config, save_config  # noqa: E402


def cmd_setup(args):
    from fpl import pipeline
    print("== FPL Edge setup: data check + model train (~1-3 min) ==")
    print("(bundled history is included; anything missing auto-downloads)")
    out = pipeline.run(team_id=args.team_id, do_backtest=args.backtest, quick=True)
    print(json.dumps(out, indent=2))
    print("Setup complete. Double-click START_DASHBOARD.bat next.")


def cmd_update(args):
    from fpl import pipeline
    out = pipeline.run(team_id=args.team_id, do_backtest=args.backtest,
                       force_live=args.force)
    print(json.dumps(out, indent=2))


def cmd_backtest(args):
    import pandas as pd
    from fpl.config import RAW
    from fpl.features import FeatureEngine
    from fpl import models as M
    from fpl.history import Dataset
    cfg = load_config()
    if (RAW / "all_history.parquet").exists() and not args.force:
        full = pd.read_parquet(RAW / "all_history.parquet")
    else:
        full = Dataset(cfg).build_all()
        full.to_parquet(RAW / "all_history.parquet")
    eng = FeatureEngine(cfg["history_seasons"] + [cfg["live_season"]]).fit_team_priors(full)
    feat = eng.build(full)
    fcols = eng.feature_cols(feat)
    rep = M.backtest(feat, fcols, cfg["history_seasons"][-1],
                     step=2 if args.quick else 1)
    print(json.dumps(rep["summary"], indent=2))


def cmd_serve(args):
    # app.py is a Streamlit application.
    import subprocess
    app_path = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path),
                    "--server.port", str(args.port),
                    "--browser.gatherUsageStats", "false"], check=True)


def cmd_status(args):
    for f in sorted(OUTPUTS.glob("*.json")) + sorted(OUTPUTS.glob("*.csv")):
        print(f"{f.name:40s} {f.stat().st_size/1024:8.1f} KB")
    p = OUTPUTS / "pipeline_status.json"
    if p.exists():
        print("\nlast pipeline:", p.read_text())


def cmd_team(args):
    cfg = load_config()
    if args.id:
        cfg["team_id"] = int(args.id)
        save_config(cfg)
    from fpl import pipeline
    from fpl.api import FPL
    fpl = FPL(cfg)
    bs = fpl.bootstrap()
    nxt = fpl.next_gw(bs)
    finished = [e["id"] for e in bs["events"] if e.get("finished")]
    proj_path = OUTPUTS / f"projections_GW{nxt['id'] if nxt else 1}.parquet"
    import pandas as pd
    proj = pd.read_parquet(proj_path)
    report = pipeline.analyse_team(cfg, fpl, bs, proj,
                                   nxt["id"] if nxt else 1,
                                   finished[-1] if finished else 0)
    print(json.dumps({k: v for k, v in report.items() if k != "players"},
                     indent=2, default=str)[:4000])


def main():
    ap = argparse.ArgumentParser(description="FPL Edge CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("--team-id", type=int, default=None)
    s.add_argument("--backtest", action="store_true",
                   help="also re-run the validation backtest (~10 min)")
    s.set_defaults(fn=cmd_setup)
    s = sub.add_parser("update"); s.add_argument("--team-id", type=int, default=None)
    s.add_argument("--backtest", action="store_true")
    s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_update)
    s = sub.add_parser("backtest")
    s.add_argument("--quick", action="store_true"); s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_backtest)
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=7860); s.set_defaults(fn=cmd_serve)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("team"); s.add_argument("--id", type=int, default=None); s.set_defaults(fn=cmd_team)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
