@echo off
title Clip Farm Studio Pro
color 0A
cls
echo ========================================================
echo        INICIANDO CLIP FARM STUDIO PRO (PORTA 8888)
echo ========================================================
echo.
echo Abrindo o navegador e iniciando servidor...
echo.

start "" "http://localhost:8888"
python run_server.py

pause
