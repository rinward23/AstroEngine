@echo off
setlocal EnableDelayedExpansion

REM Python 3.11 venv
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel setuptools

REM Install app + extras
pip install -e .
pip install -r requirements.txt
if exist requirements-optional.txt pip install -r requirements-optional.txt

REM Build launcher
REM Ensure the expected PyInstaller toolchain is available.
pip install "pyinstaller==6.10.*"
pyinstaller packaging\windows\astroengine.spec --noconfirm
if errorlevel 1 goto :error

echo ===== Portable onedir at dist\AstroEngine =====

echo ===== Building Inno Setup installer (optional) =====
where iscc.exe >nul 2>&1
if %errorlevel%==0 (
  iscc packaging\windows\installer.iss
  if errorlevel 1 goto :error
  echo Installer built under: packaging\windows\Output
) else (
  echo Inno Setup not found (iscc.exe). Skipping installer step.
)

echo DONE
exit /b 0

:error
echo Build failed. See errors above.
exit /b 1
