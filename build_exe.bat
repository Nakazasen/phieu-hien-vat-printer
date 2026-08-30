@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
) else if exist "D:\Sandbox\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=D:\Sandbox\.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"!PYTHON_EXE!" package_app.py
if errorlevel 1 (
  echo.
  echo Build that bai.
  pause
  exit /b 1
)
echo.
echo Build thanh cong. Bundle nam trong release_artifacts\install_bundle.
pause
