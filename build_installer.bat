@echo off
setlocal EnableDelayedExpansion

echo ======================================================================
echo  DONG GOI VA TAO BO CAI DAT: IN PHIEU HIEN VAT (INNO SETUP 6)
echo ======================================================================
echo.

:: 1. Tim trinh bien dich Inno Setup (ISCC.exe)
set "ISCC_PATH="

where iscc >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%I in ('where iscc 2^>nul') do (
        if not defined ISCC_PATH set "ISCC_PATH=%%I"
    )
)

if not defined ISCC_PATH (
    if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
        set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    ) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
        set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    ) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
        set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    )
)

if defined ISCC_PATH (
    echo [OK] Tim thay Inno Setup compiler tai: "!ISCC_PATH!"
) else (
    echo [CANH BAO] Khong tim thay ISCC.exe trong PATH hoac cac thu muc cai dat mac dinh.
    echo           Ban co the cai Inno Setup 6 hoac bien dich file installer\InPhieuHienVat.iss thu cong.
)
echo.

:: 2. Chon trinh thuc thi Python
set "PYTHON_EXE="
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    )
)

if not defined PYTHON_EXE (
    echo [LOI] Khong tim thay Python tren he thong (py/python).
    exit /b 1
)

:: 3. Chay script dong goi package_app.py
echo [BUOC 1/2] Dang dong goi bundle ung dung (PyInstaller onedir + launcher + manifest)...
%PYTHON_EXE% "%~dp0package_app.py"
if errorlevel 1 (
    echo [LOI] Qua trinh dong goi package_app.py that bai.
    exit /b 1
)
echo [OK] Dong goi bundle thanh cong.
echo.

:: 4. Bien dich bo cai Inno Setup neu co ISCC.exe
if defined ISCC_PATH (
    echo [BUOC 2/2] Dang bien dich bo cai dat Inno Setup (.iss)...
    "!ISCC_PATH!" "%~dp0installer\InPhieuHienVat.iss"
    if errorlevel 1 (
        echo [LOI] Bien dich Inno Setup that bai.
        exit /b 1
    )
    echo.
    echo ======================================================================
    echo  HOAN TAT! Bo cai dat da duoc tao tai:
    echo  release_artifacts\InPhieuHienVat_Setup_0.1.1.exe
    echo ======================================================================
) else (
    echo [BUOC 2/2] Bo qua tao Setup.exe vi chua cai Inno Setup 6.
    echo Bundle goc da san sang tai release_artifacts\install_bundle
)

echo.
exit /b 0
