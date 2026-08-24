# Review & Adversarial Critic Report: Inno Setup 6 Packaging & Build Automation

**Agent**: `reviewer_1` (Reviewer & Adversarial Critic)  
**Parent**: `orchestrator_pkg` (`496a12d8-5a64-4409-b089-6abdc4ab595d`)  
**Verdict**: **APPROVE**  
**Assessment Date**: 2026-08-19  

---

## 1. Observation

Direct code and configuration inspection yielded the following verbatim evidence:

### A. Inno Setup Configuration (`installer/InPhieuHienVat.iss` & `installer/languages/Vietnamese.isl`)
1. **AppId GUID Specification**:
   - `installer/InPhieuHienVat.iss:8`: `#define AppId "{{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}}"`
   - `installer/InPhieuHienVat.iss:13`: `AppId={#AppId}`
   - Observation: Proper escaping `{{...}}` compliant with Inno Setup preprocessor syntax to prevent interpreting braces as constants.
2. **Per-User Directory & Privileges**:
   - `installer/InPhieuHienVat.iss:20`: `DefaultDirName={localappdata}\InPhieuHienVat`
   - `installer/InPhieuHienVat.iss:28`: `PrivilegesRequired=lowest`
   - `installer/InPhieuHienVat.iss:27`: `ArchitecturesInstallIn64BitMode=x64compatible`
   - Observation: Zero UAC elevation prompts required during installation; files installed into user space so auto-updates can execute without administrative privilege.
3. **Shortcut Targets**:
   - `installer/InPhieuHienVat.iss:9`: `#define LauncherExe "InPhieuHienVat_Launcher.exe"`
   - `installer/InPhieuHienVat.iss:39`: `Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#LauncherExe}"`
   - `installer/InPhieuHienVat.iss:40`: `Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#LauncherExe}"; Tasks: desktopicon`
   - `installer/InPhieuHienVat.iss:46`: `Filename: "{app}\{#LauncherExe}"; Description: "Khởi chạy {#AppName}"; Flags: nowait postinstall skipifsilent`
   - Observation: All Start Menu, Desktop, and Post-install launch actions point to the root launcher `InPhieuHienVat_Launcher.exe`, ensuring transparent routing to newly updated application versions.
4. **Safe Uninstallation**:
   - `installer/InPhieuHienVat.iss:48-50`:
     ```iss
     [UninstallDelete]
     ; Dữ liệu vận hành trong LocalAppData (InPhieuHienVatData) không bao giờ bị xóa tại đây.
     Type: filesandordirs; Name: "{app}\.staging"
     ```
   - Observation: Only transient staging directories are deleted. The user operational state at `%LOCALAPPDATA%\InPhieuHienVatData` (and the shared network database) is strictly isolated and preserved.
5. **Vietnamese Localization**:
   - `installer/InPhieuHienVat.iss:33`: `Name: "vietnamese"; MessagesFile: "languages\Vietnamese.isl"`
   - `installer/languages/Vietnamese.isl:6-9`: `LanguageName=Tiếng Việt`, `LanguageID=$042A`, `LanguageCodePage=1258`.
   - Observation: Full, comprehensive Vietnamese string table for Inno Setup 6.5.0+ covering wizards, buttons, errors, tasks, and uninstaller.

### B. Packaging Pipeline & Build Automation (`package_app.py` & `build_installer.bat`)
1. **PyInstaller Onedir Dual-Binary Packaging**:
   - `package_app.py:104-118`: PyInstaller invoked with `--onedir`, `--clean`, `--noconfirm`, bundling assets (`template.pdf`, `layout_config.json`, `release.json`, `update_sources.default.json`, `app_icon.ico`, `sv_ttk`).
   - `package_app.py:126-142`: `build_application()` builds `InPhieuHienVat.exe` (GUI, windowed).
   - `package_app.py:144-148`: `build_launcher()` builds `InPhieuHienVat_Launcher.exe` (console/entrypoint).
   - `package_app.py:173-202`: `assemble_install_bundle()` constructs layout `release_artifacts/install_bundle/`:
     - Root: `InPhieuHienVat_Launcher.exe` + dependencies + `current.json`.
     - `apps/<version>/`: `InPhieuHienVat.exe` + `_internal/` + assets + `manifest.json`.
     - Manifest generation computes full SHA-256 digests and file sizes for all files.
2. **ISCC Auto-Detection Across 4 Standard Locations**:
   - `package_app.py:205-217`:
     1. `PATH` (`shutil.which("ISCC")`)
     2. `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`
     3. `%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe`
     4. `%ProgramFiles%\Inno Setup 6\ISCC.exe`
   - `build_installer.bat:9-27`: Implements the identical 4-location search order in Windows batch script with delayed expansion.
3. **Headless Smoke Test & Health Check**:
   - `slip_printer_app.py:23-28`: `--health-check` CLI switch triggers `run_health_check()`.
   - `ui/main_window.py:426-434`: `run_health_check()` validates `prepare_runtime_paths()`, `ensure_layout_config_file()`, `load_layout_config()`, and `PORegistry()` connectivity without starting the GUI mainloop.
   - `package_app.py:151-162`: `_smoke_health()` tests both `InPhieuHienVat.exe` and `InPhieuHienVat_Launcher.exe` using temporary isolated environment variables (`INPHIEUHIENVAT_DATA_DIR`, `INPHIEUHIENVAT_OUTPUT_DIR`) before finalizing the bundle.

---

## 2. Logic Chain

1. **Integrity & Authenticity**:
   - Source code contains real cryptographic hashing (`hashlib.sha256`), real manifest generation, real directory structuring, and atomic file swaps (`.tmp` / `.part` -> destination via `os.replace`).
   - No hardcoded test bypasses, no dummy stubs, and no placeholder comments detected.
2. **Architecture Compliance with MP2027**:
   - The dual-binary `HASH_ONLY_LAN` deployment pattern separates the immutable versioned bundle (`apps/<version>/`) from the permanent launcher (`InPhieuHienVat_Launcher.exe`), matching the project specification in `PROJECT.md`.
   - Manifest validation in `updater/update_launcher.py` checks both directory boundary containment (`parents` check against traversal) and exact `manifest_sha256` matching against `current.json`.
3. **Packaging Safety & User Experience**:
   - Installing under `{localappdata}\InPhieuHienVat` with `PrivilegesRequired=lowest` completely avoids Windows UAC prompts, allowing non-admin factory floor users to install and receive background LAN updates seamlessly.
   - Preserving `%LOCALAPPDATA%\InPhieuHienVatData` during uninstallation guarantees zero data loss for operational SQLite history (`po_registry.db`) and user-modified layout definitions (`layout_config.json`).
4. **Build Automation Resiliency**:
   - `package_app.py` and `build_installer.bat` fail gracefully if ISCC is not installed, building the complete raw bundle ready for manual compilation, and executing compilation automatically whenever ISCC is found.
   - Python stdout/stderr encoding is safely reconfigured to UTF-8 on Windows, preventing crashes on systems with non-UTF-8 console code pages.

---

## 3. Caveats & Adversarial Stress Testing

### Adversarial Challenges Tested:
1. **Path Traversal & DLL Hijacking Attack Surface**:
   - *Test*: Can `current.json` be poisoned with malicious relative paths (e.g. `../` or `C:\malicious.exe`)?
   - *Result*: `updater/update_launcher.py:49-55` (`_safe_entrypoint`) and lines 63-70 strictly validate that the entrypoint is a relative `.exe` inside `apps/<version>/` and that `version_dir` is a direct subpath of `app_root`.
2. **Missing Inno Setup Installation**:
   - *Test*: What happens if the developer environment does not have Inno Setup installed?
   - *Result*: Both `package_app.py` and `build_installer.bat` report an informative warning, exit with success, and leave the complete `release_artifacts/install_bundle/` intact for packaging.
3. **Inno Setup Escaped Braces**:
   - *Test*: Does Inno Setup treat `{{CEBD9EDE-...}}` as a valid AppId?
   - *Result*: In Inno Setup `.iss` syntax, doubling the opening curly brace `{{` is required to escape the GUID string. This is 100% correct.

### Minor Caveats / Non-blocking Suggestions:
- In `build_installer.bat` line 75, the completion banner prints `InPhieuHienVat_Setup_0.1.1.exe` as a static echo string. While `package_app.py` and `InPhieuHienVat.iss` dynamically use the version from `release.json`, it is recommended in future iterations to parse `release.json` dynamically in `.bat` or let `package_app.py` print the final summary. (Risk: Low / Cosmetic).

---

## 4. Conclusion

**Verdict**: **APPROVE**

The Inno Setup 6 packaging configuration (`installer/InPhieuHienVat.iss`, `installer/languages/Vietnamese.isl`), build automation pipeline (`package_app.py`, `build_installer.bat`), and headless health check system (`slip_printer_app.py --health-check`) fulfill all specifications in `PROJECT.md` and `ORIGINAL_REQUEST.md`. The implementation exhibits high engineering rigor, robust security against path traversal, complete Vietnamese localization, and per-user deployment isolation.

---

## 5. Verification Method

To independently verify all findings:
1. Inspect the Inno Setup script and language files:
   - `installer/InPhieuHienVat.iss`
   - `installer/languages/Vietnamese.isl`
2. Inspect the packaging automation scripts:
   - `package_app.py`
   - `build_installer.bat`
3. Run the automated test suite and health check:
   - `pytest tests/test_updater.py tests/test_runtime_paths.py`
   - `python slip_printer_app.py --health-check`
4. Run packaging verification:
   - `python package_app.py --no-installer`
   - Verify layout in `release_artifacts/install_bundle/` (`InPhieuHienVat_Launcher.exe`, `current.json`, `apps/0.1.1/manifest.json`).
