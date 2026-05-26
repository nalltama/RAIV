Option Explicit

Dim shell, fso, scriptDir, batchPath
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batchPath = fso.BuildPath(scriptDir, "run_raiv.bat")
shell.CurrentDirectory = scriptDir
shell.Run """" & batchPath & """", 0, False
