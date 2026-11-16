@echo off
title Clip Farm Studio Pro
color 0A
cls
echo ========================================================
echo        INICIANDO CLIP FARM STUDIO PRO (AUTO-POST)
echo ========================================================
echo.
echo Abrindo o navegador e iniciando servidor...
echo.

start "" "http://localhost:8000"
python run_server.py

pause
