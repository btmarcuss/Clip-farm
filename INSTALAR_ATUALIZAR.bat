@echo off
title Instalador Clip Farm Pro
color 0B
cls
echo ========================================================
echo        INSTALADOR DE DEPENDENCIAS CLIP FARM PRO
echo ========================================================
echo.
echo Instalando bibliotecas necessarias via pip...
echo.

pip install -r requirements.txt imageio-ffmpeg

echo.
echo ========================================================
echo        INSTALACAO CONCLUIDA COM SUCESSO!
echo ========================================================
echo.
echo Agora execute INICIAR_CLIP_FARM.bat para abrir o aplicativo.
echo.
pause
