@echo off
setlocal

set TARGET=C:\ValirianEtiquetas\ValirianEtiquetas.exe
set SHORTCUT=%USERPROFILE%\Desktop\ValirianEtiquetas.lnk

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%'); ^
  $s.TargetPath='%TARGET%'; ^
  $s.WorkingDirectory='C:\\ValirianEtiquetas'; ^
  $s.IconLocation='%TARGET%,0'; ^
  $s.Save()"

echo [OK] Atalho criado na área de trabalho.
endlocal

