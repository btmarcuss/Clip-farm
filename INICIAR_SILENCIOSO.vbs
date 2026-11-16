Set WshShell = CreateObject("WScript.Shell")
' Obtem o diretorio onde o proprio script VBS reside
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Executa o launcher em modo 100% oculto (0 = vbHide)
WshShell.Run "cmd.exe /c pushd """ & scriptDir & """ && python run_server.py", 0, False

' Aguarda 1.5s e abre o navegador
WScript.Sleep 1500
WshShell.Run "http://localhost:8888"
