# Handoff Report: Deep Investigation of MP2027 Packaging, Inno Setup & Auto-Update Engine

**Date**: 2026-08-19  
**Agent**: `survey_explorer_1` (Exploration Subagent)  
**Target Reference Repo**: `D:\Sandbox\MP2027`  
**Purpose**: Comprehensive investigation of packaging architecture, Inno Setup `.iss` scripts, build automation pipelines, and Auto-Update runtime engine to enable exact replication in `PM_in_lai_phieuhienvat`.

---

## 1. Observation

Direct observations from examining the codebase, configuration files, scripts, and documentation in `D:\Sandbox\MP2027`:

### 1.1 Documentation & Architecture Overview
- **Handover Playbook (`D:\Sandbox\MP2027\docs\handover\release_update_playbook.md`)**:
  - The project operates under a strict **`HASH_ONLY_LAN`** security model (lines 3-8, 35-44).
  - No private/public signing keys or certificate provisioning are used. Trust boundary is based on the company-controlled LAN share + SHA-256 hash checks + manifest file validation.
  - Software/Setup folder:
    `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan`
  - Update Catalog & Packages folder:
    `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update`
  - Canonical version source of truth: `release_update\latest.json` on LAN (lines 45-65).
  - Anti-overwrite rule: If package exists with different SHA-256, halt immediately. Atomic publishing using `.part` temporary files before renaming to `.exe` / `.mpupdate` / `latest.json`.
- **System Architecture (`D:\Sandbox\MP2027\docs\architecture\system_architecture.md`)**:
  - Release layout (lines 90-101):
    ```text
    <install-root>/
    ├── MP2027_Launcher.exe       # Thin stable launcher
    ├── current.json              # Version pointer {version, entrypoint, manifest_sha256}
    ├── _internal/                # Launcher dependencies
    └── apps/<version>/           # Immutable versioned app folder
        ├── manifest.json         # Full file inventory + sha256 + size
        ├── MP2027_Portable.exe   # Application entrypoint
        └── _internal/            # App dependencies & assets
    ```
  - App installed per-user under `%LOCALAPPDATA%\<AppName>` (`PrivilegesRequired=lowest`) so updater can stage and activate versions without requiring Windows UAC administrator elevation (lines 103-104).
  - Mutable user business data and SQLite databases reside outside the application folder in `%LOCALAPPDATA%\MPManager\Projects\...` or user-specified network paths.

---

### 1.2 Inno Setup Script (`D:\Sandbox\MP2027\installer\MP2027_Manager.iss`)

Full script structure and breakdown:
```iss
; Trình cài đặt Windows ban đầu cho MP2027 Manager
; Biên dịch bằng Inno Setup 6 sau khi chạy: py scripts/package_app.py
; Cài bộ ứng dụng onedir theo phiên bản; máy đích không cần cài Python.

#define AppName "MP2027 Manager"
#define AppVersion "0.1.6"
#define AppPublisher "MP2027"
#define LauncherExe "MP2027_Launcher.exe"
#define BundleDir "..\\release_artifacts\\install_bundle"

[Setup]
AppId={{9E4E0A87-1D0C-4A12-9F5C-93F65E4B2027}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; Cài theo người dùng vì apps/<version>, current.json và .staging là trạng thái cập nhật
; có thể thay đổi, thuộc quyền sở hữu của người dùng thông thường.
DefaultDirName={localappdata}\\MP2027 Manager
DefaultGroupName={#AppName}
OutputDir=..\\release_artifacts
OutputBaseFilename=MP2027_Manager_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName={#AppName}

[Languages]
; Bản dịch được ghim và kiểm tra đủ key so với Default.isl của Inno Setup 6.7.3.
Name: "vietnamese"; MessagesFile: "languages\Vietnamese.isl"

[Files]
Source: "{#BundleDir}\\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\\{#AppName}"; Filename: "{app}\\{#LauncherExe}"
Name: "{autodesktop}\\{#AppName}"; Filename: "{app}\\{#LauncherExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Tạo lối tắt trên màn hình nền"; GroupDescription: "Lối tắt bổ sung:"

[Run]
Filename: "{app}\\{#LauncherExe}"; Description: "Khởi chạy {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Dữ liệu vận hành/dự án trong LocalAppData không bao giờ bị xóa tại đây.
Type: filesandordirs; Name: "{app}\\.staging"
```

**Key Section Details**:
1. **`[Setup]`**:
   - `AppId`: Unique GUID identifier for uninstaller registry recognition.
   - `DefaultDirName={localappdata}\\MP2027 Manager`: Essential setting that installs the application under `%LOCALAPPDATA%`, giving the standard Windows user full write access to add new version folders (`apps/<version>`) and update `current.json`.
   - `PrivilegesRequired=lowest`: Never prompts for UAC elevation during installation.
   - `Compression=lzma2`, `SolidCompression=yes`: Maximum compression efficiency.
   - `ArchitecturesInstallIn64BitMode=x64compatible`: Ensures 64-bit installation mode.
2. **`[Languages]`**:
   - Uses `languages\Vietnamese.isl` (pinned from `jrsoftware/issrc` with 296/296 localized Vietnamese keys, CodePage 1258).
3. **`[Files]`**:
   - `Source: "{#BundleDir}\\*" DestDir: "{app}"`: Copies the entire assembled `install_bundle` (`MP2027_Launcher.exe`, `current.json`, `_internal`, `apps/0.1.6/...`).
4. **`[Icons]` & `[Tasks]`**:
   - Creates Start Menu shortcut under `{autoprograms}` and Desktop shortcut under `{autodesktop}` pointing to `MP2027_Launcher.exe`.
5. **`[Run]`**:
   - Offers post-install launch: `Flags: nowait postinstall skipifsilent`.
6. **`[UninstallDelete]`**:
   - Deletes transient staging directory `{app}\.staging`.
   - User database and configuration files in `%LOCALAPPDATA%\...` are protected and not touched during uninstallation.
7. **Pascal `[Code]`**:
   - No Pascal scripting is needed in `.iss` because version resolution and update checks are cleanly handled inside Python by the launcher and app update services.

---

### 1.3 Build Automation Scripts

#### A. PyInstaller Spec Files
1. **Application Spec (`D:\Sandbox\MP2027\MP2027_Portable.spec`)**:
   - Entry point: `packaging\mp2027_portable_entry.py`.
   - Data bundles: `assets/`, `release.json`, `update_sources.default.json`, `docs/MP2027/FORM.xlsx`, raw CSV seed templates.
   - Excludes heavy/unused libraries: `PyQt5`, `PyQt6`, `PySide2`, `PySide6`, `cv2`, `torch`, `scipy`, `matplotlib`, `transformers`, etc.
   - Mode: `COLLECT` onedir mode (`MP2027_Portable`), icon: `assets\app_icon.ico`, `console=False`, `hide_console="minimize-late"`.
2. **Launcher Spec (`D:\Sandbox\MP2027\MP2027_Manager.spec`)**:
   - Entry point: `scripts\update_launcher.py`.
   - Excludes all large numerical/ML/UI libraries: `excludes=["cv2", "numpy", "pandas", "PIL", "scipy", "torch"]`.
   - Fast, tiny onedir executable (`MP2027_Launcher.exe`).

#### B. Packaging Pipeline (`D:\Sandbox\MP2027\scripts\package_app.py`)
- **Step 1: Application Build (`_build(APP_SPEC_PATH)`)**:
  Executes `py -m PyInstaller --clean --noconfirm MP2027_Portable.spec` generating `dist/MP2027_Portable/`.
- **Step 2: Dist Validation (`_validate_dist`)**:
  Verifies required artifacts exist: `MP2027_Portable.exe`, `_internal/assets/app_icon.ico`, `_internal/docs/MP2027/FORM.xlsx`, `_internal/release.json`, `_internal/update_sources.default.json`.
- **Step 3: Packaged Health Check (`smoke_packaged_health`)**:
  Executes `dist/MP2027_Portable/MP2027_Portable.exe --health-check` in an isolated environment (`LOCALAPPDATA=build/packaged-health-smoke`).
- **Step 4: Launcher Build (`_build(LAUNCHER_SPEC_PATH)`)**:
  Executes `py -m PyInstaller --clean --noconfirm MP2027_Manager.spec` generating `dist/MP2027_Launcher/`.
- **Step 5: Bundle Assembly (`assemble_install_bundle`)**:
  - Clears `release_artifacts/install_bundle/`.
  - Places launcher files in root of bundle.
  - Places portable app in `release_artifacts/install_bundle/apps/<version>/`.
  - Writes `apps/<version>/manifest.json` (canonical JSON).
  - Writes `install_bundle/current.json` with version, entrypoint, and manifest sha256 hash.
- **Step 6: Launcher Health Check (`smoke_launcher_health`)**:
  Executes `release_artifacts/install_bundle/MP2027_Launcher.exe --health-check`.
- **Step 7: Inno Setup Compilation**:
  `& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\MP2027_Manager.iss"` compiles `release_artifacts\MP2027_Manager_Setup_<version>.exe`.
- **Step 8: Update Package Creation (`--build-update`)**:
  - Function `build_hash_checked_update`:
    - Inventories all files in `dist/MP2027_Portable/` (`_application_inventory`).
    - Calculates SHA-256 and size for every single file.
    - Generates `manifest.json` containing: `schema: 1`, `kind: "application"`, `id: "MP2027_Manager"`, `version`, `min_app_version`, `database_schema`, `health_check: "--health-check"`, `entrypoint: "MP2027_Portable.exe"`, `files: [...]`.
    - Creates ZIP archive `.mpupdate` with standard timestamp `(1980, 1, 1, 0, 0, 0)` for reproducible byte builds.
  - Function `publish_update`:
    - Copies `.mpupdate` to target folder as `.mpupdate.part`.
    - Verifies copied SHA-256.
    - Renames `.part` to final `.mpupdate`.
    - Writes `latest.json.part` with metadata: `schema: 1`, `channel`, `version`, `package`, `sha256`, `size`, `notes`.
    - Atomically renames `latest.json.part` to `latest.json`.

---

### 1.4 Auto-Update Engine Architecture

The update system is modularized into 3 core services:
1. `src/services/update_delivery.py`: Discovery, remote network/HTTP reading, catalog parsing, download.
2. `src/services/update_security.py`: Manifest verification, SHA-256 checking, zip slip prevention, safe extraction.
3. `src/services/app_updates.py`: Staging, health checking, database backup, activation, rollback, restart.

#### A. Version Checking & Semantic Comparison
- Regex: `_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")`
- Parsed to 3-tuple `(major, minor, patch)` of integers.
- Comparison:
  ```python
  def _version(value: str) -> tuple[int, int, int]:
      match = _SEMVER.fullmatch(str(value))
      if not match:
          raise UpdateDeliveryError(f"Phiên bản cập nhật không hợp lệ: {value}")
      return tuple(int(part) for part in match.groups())

  # Check eligible update:
  eligible = [item for item in found if _version(item.version) > _version(current_version)]
  best_candidate = max(eligible, key=lambda item: _version(item.version), default=None)
  ```
- Rejects downgrades (`target_version <= current_version`) and checks minimum baseline (`current_version >= manifest["min_app_version"]`).

#### B. Remote Network Share Configuration & Discovery
- Structure of `update_sources.default.json`:
  ```json
  {
    "schema": 1,
    "startup_check": true,
    "sources": [
      {
        "type": "folder",
        "location": "\\\\fstvn01\\Data\\00_KDTVN Common(KDTVN共通)\\⑤Production Engineering(製造技術)\\Hang muc can luu\\Vinh\\MP Saisan\\release_update",
        "enabled": true
      }
    ]
  }
  ```
- Configuration priority resolution (`load_update_config`):
  1. Default: `update_sources.default.json` (inside app bundle)
  2. User override: `%LOCALAPPDATA%\...\update_sources.json`
  3. Company policy override: `%PROGRAMDATA%\MPManager\update_sources.json` (highest priority)
- Catalog file `latest.json`:
  ```json
  {
    "schema": 1,
    "channel": "pilot",
    "version": "0.1.6",
    "package": "MP2027_Manager-0.1.6.mpupdate",
    "sha256": "226c4de8f62162d3abb22af60783ab6fe0a50ee5522d0da2b49a8b5cf5a79e17",
    "size": 84082684,
    "notes": "• Sửa lỗi\n• Thêm tính năng"
  }
  ```
- Folder discovery logic (`discover_folder_updates`):
  - Reads `latest.json` if present.
  - Validates `package_name`, checks `sha256` and file size.
  - Inspects package inner `manifest.json` via `_verified_folder_candidate`.
  - Fallback: Scans `*.mpupdate` files in folder if `latest.json` is missing.

#### C. Download, Integrity Verification & Staging
- `fetch_update_candidate` in `update_delivery.py`:
  - Streams file to `%LOCALAPPDATA%\...\.updates\downloads\download-*.tmp`.
  - Enforces `MAX_DOWNLOAD_BYTES = 512MB`.
  - Verifies downloaded byte count matches `candidate.size`.
  - Verifies computed `sha256_file(tmp)` matches `candidate.sha256`.
  - Atomically replaces temp file with `MP2027_Manager_<version>.mpupdate`.
- `stage_application_update` in `app_updates.py`:
  - Validates manifest requirements (`database_schema >= CURRENT_SCHEMA_VERSION`, `entrypoint` exists, `health_check == "--health-check"`).
  - Unzips to `.staging/app-<random>` using `safe_extract_zip`:
    * Rejects zip bombs, directory traversal (`..`), absolute paths, colon drive paths.
  - Calls `verify_manifest_files`: calculates SHA-256 and byte size for every extracted file against `manifest["files"]`.
  - Moves `.staging/app-<random>` to `apps/<version>`.

#### D. Safety Health-Check & Database Backup
- `run_staged_health`:
  - Runs `<app_root>\apps\<version>\MP2027_Portable.exe --health-check` in an isolated environment (`LOCALAPPDATA=<app_root>\.health`).
  - Timeout: 60 seconds. Must return exit code 0.
- `backup_runtime_databases`:
  - Scans all `.db`, `.sqlite`, `.sqlite3` files in runtime directory.
  - Copies to `<app_root>\backups\before-<target_version>\`.
  - Writes `backup.json` inventory with SHA-256 and sizes.

#### E. Activation, Rollback & Pointer Switch
- `activate_staged_update`:
  - Reads existing `current.json` and writes it to `previous.json`.
  - Writes new `current.json.tmp` with:
    ```json
    {
      "schema": 1,
      "version": "0.1.6",
      "entrypoint": "MP2027_Portable.exe",
      "manifest_sha256": "..."
    }
    ```
  - Atomically replaces `current.json.tmp` -> `current.json`.
- `rollback_activation`:
  - If a newly activated version fails, swaps `previous.json` back into `current.json`.

#### F. Process Termination & Clean Handover / Restart
1. **Spawn New Process (`launch_activated_update`)**:
   ```python
   def launch_activated_update(app_root, *, current_pid=None, popen=subprocess.Popen) -> Path:
       entrypoint = resolve_current_entrypoint(app_root)
       pid = int(current_pid if current_pid is not None else os.getpid())
       command = [str(entrypoint), "--wait-for-pid", str(pid)]
       kwargs = {
           "cwd": str(entrypoint.parent),
           "close_fds": True,
       }
       if os.name == "nt":
           kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
       popen(command, **kwargs)
       return entrypoint
   ```
2. **Old Process Exits (`universal_app.py:2140-2141`)**:
   - Calls `self.root.quit()` and `self.root.destroy()`.
3. **New Process Waits for Old Process Exit (`packaging/mp2027_portable_entry.py:13-58`)**:
   - Parses `--wait-for-pid <pid>`.
   - Loops checking `os.kill(pid, 0)` with `time.sleep(0.1)` up to 120 seconds.
   - Once old PID is gone, proceeds to initialize UI.

#### G. Background Threading & UI Flow
- **Startup Check (`universal_app.py:1171, 1956-1986`)**:
  - Scheduled 1.2s after window opens: `self.root.after(1200, self._start_update_discovery)`.
  - Spawns daemon thread `threading.Thread(target=worker, daemon=True).start()`.
  - UI thread dispatch: `self._run_on_ui_thread(self._offer_discovered_update, candidate, app_root, current_version)` which uses `self.root.after(0, ...)`.
- **User Prompt (`_offer_discovered_update`)**:
  - `messagebox.askyesno("Có bản cập nhật MP2027", ...)` displaying version and release notes.
- **Download & Install Worker (`_install_discovered_update`)**:
  - Runs in background daemon thread while setting `self._application_update_running = True` and updating log status.
  - On finish, dispatches `self._finish_application_update` on UI thread.
  - Shows `messagebox.showinfo("Đã cài bản cập nhật", ...)`, triggers `launch_activated_update`, and shuts down.
- **Manual Menu Check (`install_application_update`)**:
  - Triggered by menu item: "Cài bản cập nhật...".
  - Scans all enabled sources. If no update, shows `messagebox.showinfo("Đang dùng phiên bản mới nhất", ...)`. If update found, offers installation dialog.

#### H. Error Handling & Resilience
- **Network timeouts**: Default socket timeout 5.0s for discovery, 30.0s for downloads.
- **Unreachable UNC / Offline Network**: `check_update_source` catches `OSError` / network path unreachable; ignores or logs gracefully without crashing UI.
- **Corrupted / Partial Files**: Ignored during discovery; during download, `.part` and `.tmp` files prevent half-written packages. If checksum fails, temp files are unlinked and error is reported.
- **Failed Health Check**: If new version executable fails `--health-check`, staging directory is purged, `current.json` is untouched, and update aborts safely.
- **Permission Errors**: Because installation is under `%LOCALAPPDATA%`, write operations succeed without admin rights.

---

## 2. Logic Chain

1. **Packaging Strategy Rationale**:
   - *Observation*: PyInstaller single-file mode (`onefile`) is notoriously slow to start (extracts all `.dll`s to `%TEMP%` on every run) and prevents clean atomic patching.
   - *Inference*: The reference project uses `onedir` mode structured into immutable version directories (`apps/<version>/`) and a lightweight, permanent `MP2027_Launcher.exe`.
   - *Conclusion*: For `PM_in_lai_phieuhienvat`, adopting PyInstaller `onedir` + thin launcher + Inno Setup gives instant startup time and enables in-place zero-elevation auto-updates.

2. **Inno Setup & Privilege Model**:
   - *Observation*: `MP2027_Manager.iss` specifies `DefaultDirName={localappdata}\...` and `PrivilegesRequired=lowest`.
   - *Inference*: Installing to `%LOCALAPPDATA%` eliminates UAC prompts during initial installation and allows the Python update engine to create new folders and write files without requesting admin elevation.
   - *Conclusion*: `PM_in_lai_phieuhienvat`'s Inno Setup script must follow this exact per-user setup pattern.

3. **Trust & Verification Model (`HASH_ONLY_LAN`)**:
   - *Observation*: Managing asymmetric signing keys in an internal corporate environment creates credential storage risks and build fragility.
   - *Inference*: Placing update artifacts in a restricted company LAN share (`\\fstvn01\...`) and verifying SHA-256 at both catalog level (`latest.json`) and file level (`manifest.json`) provides strong integrity protection against transmission errors or unauthorized tampering without key management overhead.
   - *Conclusion*: `PM_in_lai_phieuhienvat` should copy this exact `HASH_ONLY_LAN` architecture.

4. **Zero-Downtime Clean Process Handover**:
   - *Observation*: Windows file locking prevents replacing running executables.
   - *Inference*: By installing versions into side-by-side folders (`apps/0.1.0/`, `apps/0.1.1/`) and switching a JSON pointer (`current.json`), existing running processes never experience file lock collisions. The `--wait-for-pid <pid>` argument ensures the new version waits until the old GUI process closes before rendering its window.
   - *Conclusion*: This process replacement mechanism is completely robust and portable to any Tkinter desktop app.

---

## 3. Caveats

1. **Network Share Permissions**:
   - The developer machine must have read/write access to the target UNC network share (`\\fstvn01\...` or configured IP) during publishing.
   - Client machines only require read access to check and fetch updates.
2. **Inno Setup 6 Installation**:
   - Building the final `Setup.exe` requires Inno Setup 6 (specifically `ISCC.exe` at `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` or on PATH).
3. **Application Specific Paths for `PM_in_lai_phieuhienvat`**:
   - In `MP2027`, the network path is:
     `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\MP Saisan\release_update`
   - In `PM_in_lai_phieuhienvat`, the target network share will be:
     `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update` (or as configured).
   - Application AppId, AppName, and AppVersion must be customized to `PM_in_lai_phieuhienvat`.

---

## 4. Conclusion

The reference project `D:\Sandbox\MP2027` contains a mature, production-proven Windows desktop packaging and auto-update architecture:
1. **Packaging**: PyInstaller `onedir` build with two spec files (`app.spec` for heavy app, `launcher.spec` for thin launcher) + automated health-check smoke testing.
2. **Installer**: Inno Setup 6 `.iss` script using Vietnamese localization (`Vietnamese.isl`), per-user `%LOCALAPPDATA%` installation, `PrivilegesRequired=lowest`, and modern wizard UI.
3. **Auto-Update Engine**:
   - `update_delivery.py`: UNC / HTTPS discovery, atomic `.part` downloading, SHA-256 verification, semver comparison.
   - `update_security.py`: Manifest validation, zip-slip protection, file-by-file hash & size verification.
   - `app_updates.py`: Staging, pre-activation health checking, automated database backup, atomic pointer switching (`current.json`), process handover via `--wait-for-pid`.
   - `universal_app.py`: Background threaded checking, non-blocking UI startup check, friendly Vietnamese dialogs, smooth application restart.

All components are modular, decoupled from domain logic, and directly portable to `PM_in_lai_phieuhienvat`.

---

## 5. Verification Method

To independently verify all findings in `D:\Sandbox\MP2027`:

1. **Verify Inno Setup Script & Language File**:
   ```powershell
   Get-Content -Path "D:\Sandbox\MP2027\installer\MP2027_Manager.iss"
   Get-Item -Path "D:\Sandbox\MP2027\installer\languages\Vietnamese.isl"
   ```
2. **Verify Automated Packaging & Spec Files**:
   ```powershell
   Get-Content -Path "D:\Sandbox\MP2027\MP2027_Portable.spec"
   Get-Content -Path "D:\Sandbox\MP2027\MP2027_Manager.spec"
   Get-Content -Path "D:\Sandbox\MP2027\scripts\package_app.py"
   ```
3. **Run Update Service Unit Tests**:
   ```powershell
   py -m pytest "D:\Sandbox\MP2027\tests\test_app_updates.py" "D:\Sandbox\MP2027\tests\test_update_delivery.py" "D:\Sandbox\MP2027\tests\test_update_security.py" -q
   ```
   *Expected result*: All unit tests pass, confirming the integrity and contracts of the auto-update services.
4. **Inspect UI Integration in Universal App**:
   ```powershell
   Select-String -Path "D:\Sandbox\MP2027\src\universal_app.py" -Pattern "discover_available_update|install_runtime_application_update|launch_activated_update"
   ```
