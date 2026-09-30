@echo off
title FPL Edge - Setup (one time)
echo ============================================================
echo   FPL EDGE - SETUP (run this once)
echo ============================================================
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.10+ from python.org
  echo         and tick "Add Python to PATH", then run this again.
  pause
  exit /b 1
)
echo [1/3] Installing packages (Streamlit, pandas, XGBoost, scikit-learn, scipy, pyarrow)...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
  echo.
  echo [WARN] pip install had issues. Try:  python -m pip install --upgrade pip
  pause
)
echo.
echo [2/3] Verifying data and training models (bundled history included;
echo       anything missing auto-downloads). Takes ~1-3 minutes.
python cli.py setup
echo.
echo [3/3] Done! Double-click START_DASHBOARD.bat to open the dashboard.
echo       Optional: REVALIDATE_MODEL.bat re-runs the full backtest.
echo.
pause
