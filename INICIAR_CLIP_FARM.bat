@echo off
pushd "%~dp0"

:: Executa o inicializador em segundo plano sem janela de console
start "" wscript.exe "%~dp0INICIAR_SILENCIOSO.vbs"

popd
exit
