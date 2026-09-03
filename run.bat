@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

:: Tim Python co day du thu vien can thiet
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
        %%~P -c "import customtkinter, fitz, openpyxl" >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_EXE=%%~P"
        )
    )
)

if defined PYTHON_EXE (
    if exist "%~dp0slip_printer_app.py" (
        "!PYTHON_EXE!" "%~dp0slip_printer_app.py" %*
        if errorlevel 1 pause
        exit /b !errorlevel!
    )
)

if exist "%~dp0dist\InPhieuHienVat\InPhieuHienVat.exe" (
    "%~dp0dist\InPhieuHienVat\InPhieuHienVat.exe" %*
    if errorlevel 1 pause
    exit /b %errorlevel%
)

if exist "%~dp0release_artifacts\install_bundle\InPhieuHienVat_Launcher.exe" (
    "%~dp0release_artifacts\install_bundle\InPhieuHienVat_Launcher.exe" %*
    if errorlevel 1 pause
    exit /b %errorlevel%
)

echo ======================================================================
echo [LOI] Khong tim thay Python co cai dat thu vien (customtkinter, fitz).
echo Hoac khong tim thay file thuc thi (.exe) InPhieuHienVat.
echo.
echo Vui long kiem tra lai Python hoac chay:
echo   pip install -r requirements.txt
echo ======================================================================
pause
exit /b 1
