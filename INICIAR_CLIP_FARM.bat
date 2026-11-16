@echo off
title Clip Farm Studio Pro
color 0A
cls

:: Resolve o problema de pastas de rede compartilhada (UNC) no Windows
pushd "%~dp0"

echo ========================================================
echo        INICIANDO CLIP FARM STUDIO PRO (PORTA 8888)
echo ========================================================
echo.
echo Diretorio de execucao: %CD%
echo.
echo Aguarde 2 segundos para o servidor subir...
echo.

:: Inicia o servidor Python em segundo plano ou em janela dedicada
start "" "http://localhost:8888"

python run_server.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Ocorreu um problema ao iniciar o servidor Python.
    echo Verifique as mensagens acima.
    pause
)

popd
