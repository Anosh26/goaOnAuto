Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
strToolsDir = fso.GetParentFolderName(strScriptDir)
strProjectDir = fso.GetParentFolderName(strToolsDir)

' Run pythonw.exe completely hidden (0 window style) without console window
WshShell.CurrentDirectory = strProjectDir
WshShell.Run "pythonw.exe """ & strScriptDir & "\tray_service.py""", 0, False
