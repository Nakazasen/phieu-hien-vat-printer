@echo off
setlocal
cd /d "%~dp0"
python package_app.py
if errorlevel 1 (
  echo.
  echo Build that bai.
  pause
  exit /b 1
)
echo.
echo Build thanh cong. Bundle nam trong release_artifacts\install_bundle.
pause
