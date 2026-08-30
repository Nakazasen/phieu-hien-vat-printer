@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

:: Tim Python tu .venv hoac duong dan he thong
set "PYTHON_EXE="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
) else if exist "D:\Sandbox\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=D:\Sandbox\.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    )
)

if exist "%~dp0slip_printer_app.py" (
    if defined PYTHON_EXE (
        "!PYTHON_EXE!" "%~dp0slip_printer_app.py"
        if errorlevel 1 pause
        exit /b !errorlevel!
    )
)

if exist "%~dp0dist\InPhieuHienVat\InPhieuHienVat.exe" (
    "%~dp0dist\InPhieuHienVat\InPhieuHienVat.exe"
    if errorlevel 1 pause
    exit /b %errorlevel%
)

if exist "%~dp0release_artifacts\install_bundle\InPhieuHienVat.exe" (
    "%~dp0release_artifacts\install_bundle\InPhieuHienVat.exe"
    if errorlevel 1 pause
    exit /b %errorlevel%
)

echo Khong tim thay Python de chay slip_printer_app.py hoac file InPhieuHienVat.exe.
pause
exit /b 1
