@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PYTHON_EXE="

for %%P in (
    "%~dp0.venv\Scripts\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "python"
    "py"
    "%~dp0..\.venv\Scripts\python.exe"
    "D:\Sandbox\.venv\Scripts\python.exe"
) do (
    if not defined PYTHON_EXE (
        %%~P -c "import PyInstaller, customtkinter" >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_EXE=%%~P"
        )
    )
)

if not defined PYTHON_EXE (
    echo [LOI] Khong tim thay Python co cai dat PyInstaller va cac thu vien can thiet.
    pause
    exit /b 1
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
