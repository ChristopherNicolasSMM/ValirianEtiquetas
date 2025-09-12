@echo off
setlocal

REM Build executável com PyInstaller
if not exist .venv (echo [INFO] Certifique-se de estar no venv / dependencias instaladas)

python -m pip install --upgrade pip
python -m pip install pyinstaller

pyinstaller --clean --noconfirm pyinstaller.spec

echo.
echo [OK] Build concluido. Veja a pasta 'dist/ValirianEtiquetas'.
endlocal

