@echo off
title FPL Edge - Full Model Revalidation
echo Re-running the leakage-free backtest on 2025/26 (~5-10 min)...
python cli.py backtest --quick
pause
