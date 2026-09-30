@echo off
title FPL Edge - Weekly Update
echo ============================================================
echo   FPL EDGE - weekly update (run after each gameweek)
echo   fetches live data, retrains, refreshes projections,
echo   team analysis, transfer plans, season plan
echo ============================================================
python cli.py update
echo.
echo Done. Open the dashboard (START_DASHBOARD.bat) to see results.
pause
