@echo off
title Instalador Clip Farm Pro
color 0B
cls

pushd "%~dp0"

echo ========================================================
echo        INSTALADOR DE DEPENDENCIAS CLIP FARM PRO
echo ========================================================
echo.
echo Diretorio atual: %CD%
echo Instalando dependencias necessarias...
echo.

pip install -r requirements.txt imageio-ffmpeg

echo.
echo ========================================================
echo        INSTALACAO CONCLUIDA!
echo ========================================================
echo.
pause

popd
