@echo off
title FPL Edge - Dashboard (Streamlit)
echo ============================================================
echo   FPL EDGE - starting dashboard...
echo   The browser opens at http://localhost:7860
echo   (keep this window open while using it)
echo ============================================================
start "" http://localhost:7860
python -m streamlit run app.py --server.port 7860 --browser.gatherUsageStats false
pause
