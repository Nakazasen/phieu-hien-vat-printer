@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0slip_printer_app.py" (
    python "%~dp0slip_printer_app.py"
    if errorlevel 1 pause
    exit /b %errorlevel%
)

if exist "%~dp0dist\InPhieuHienVat\InPhieuHienVat.exe" (
    "%~dp0dist\InPhieuHienVat\InPhieuHienVat.exe"
    if errorlevel 1 pause
    exit /b %errorlevel%
)

echo Khong tim thay dist\InPhieuHienVat\InPhieuHienVat.exe hoac slip_printer_app.py.
pause
exit /b 1
