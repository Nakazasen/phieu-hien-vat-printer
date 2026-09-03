"""Build the versioned onedir bundle consumed by Inno Setup and the updater."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001, S110
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001, S110
            pass


PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "InPhieuHienVat"
LAUNCHER_NAME = "InPhieuHienVat_Launcher"
APP_ENTRYPOINT = f"{APP_NAME}.exe"
APP_DIST = PROJECT_ROOT / "dist" / APP_NAME
LAUNCHER_DIST = PROJECT_ROOT / "dist" / LAUNCHER_NAME
RELEASE_ARTIFACTS = PROJECT_ROOT / "release_artifacts"
INSTALL_BUNDLE = RELEASE_ARTIFACTS / "install_bundle"
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

DEFAULT_LAN_SETUP_DIR = r"\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI"
DEFAULT_LAN_UPDATE_DIR = r"\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update"



def _release() -> dict[str, Any]:
    value = json.loads((PROJECT_ROOT / "release.json").read_text(encoding="utf-8-sig"))
    version = str(value.get("version", ""))
    if not SEMVER.fullmatch(version):
        raise ValueError("release.json phải có version dạng major.minor.patch")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory(root: Path) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "manifest.json"):
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
        )
    if not files:
        raise RuntimeError(f"Bundle rỗng: {root}")
    return files


def _remove_disallowed_bundle_files(root: Path) -> None:
    """Remove metadata files whose paths are rejected by the secure updater."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            path.unlink()


def _validate_app_dist(root: Path) -> None:
    # PyInstaller --onedir keeps application resources under _internal while
    # the executable stays at the bundle root.  Keep this validation aligned
    # with runtime_paths.bundle_root(), which resolves to sys._MEIPASS.
    resource_root = root / "_internal"
    required = [
        root / APP_ENTRYPOINT,
        resource_root / "template.pdf",
        resource_root / "layout_config.json",
        resource_root / "release.json",
        resource_root / "update_sources.default.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Bundle app thiếu file bắt buộc:\n- " + "\n- ".join(missing))


def _run_pyinstaller(
    script: Path,
    name: str,
    *,
    add_data: list[Path],
    console: bool,
    icon: Path,
) -> Path:
    arguments = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        name,
        "--distpath",
        str(PROJECT_ROOT / "dist"),
        "--workpath",
        str(PROJECT_ROOT / "build" / name),
        "--specpath",
        str(PROJECT_ROOT / "build" / "specs"),
        "--icon",
        str(icon),
        "--collect-data",
        "sv_ttk",
    ]
    arguments.append("--console" if console else "--windowed")
    for path in add_data:
        arguments.extend(["--add-data", f"{path}{os.pathsep}."])
    arguments.append(str(script))
    subprocess.run(arguments, check=True, cwd=str(PROJECT_ROOT))
    return PROJECT_ROOT / "dist" / name


def build_application() -> Path:
    icon = PROJECT_ROOT / "app_icon.ico"
    assets = [
        PROJECT_ROOT / "template.pdf",
        PROJECT_ROOT / "layout_config.json",
        PROJECT_ROOT / "release.json",
        PROJECT_ROOT / "update_sources.default.json",
        icon,
    ]
    if (PROJECT_ROOT / "DummySlip.xlsx").is_file():
        assets.append(PROJECT_ROOT / "DummySlip.xlsx")
    root = _run_pyinstaller(
        PROJECT_ROOT / "slip_printer_app.py", APP_NAME, add_data=assets, console=False, icon=icon
    )
    _remove_disallowed_bundle_files(root)
    _validate_app_dist(root)
    return root


def build_launcher() -> Path:
    icon = PROJECT_ROOT / "app_icon.ico"
    root = _run_pyinstaller(
        PROJECT_ROOT / "updater" / "update_launcher.py", LAUNCHER_NAME, add_data=[], console=True, icon=icon
    )
    _remove_disallowed_bundle_files(root)
    return root


def _smoke_health(executable: Path, *, app_root: Path | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="inphieuhienvat-health-") as temp:
        temp_root = Path(temp)
        environment = os.environ.copy()
        environment["INPHIEUHIENVAT_DATA_DIR"] = str(temp_root / "data")
        environment["INPHIEUHIENVAT_OUTPUT_DIR"] = str(temp_root / "output")
        command = [str(executable)]
        if app_root is not None:
            command.extend(["--app-root", str(app_root)])
        command.append("--health-check")
        subprocess.run(command, check=True, cwd=str(executable.parent), env=environment, timeout=180)


def _validate_inno_version(version: str) -> None:
    script = PROJECT_ROOT / "installer" / "InPhieuHienVat.iss"
    if not script.is_file():
        raise FileNotFoundError(f"Thiếu Inno Setup script: {script}")
    text = script.read_text(encoding="utf-8")
    if f'#define AppVersion "{version}"' not in text:
        raise RuntimeError("Version trong installer/InPhieuHienVat.iss không khớp release.json")


def assemble_install_bundle(app_dist: Path, launcher_dist: Path) -> Path:
    release = _release()
    version = str(release["version"])
    if INSTALL_BUNDLE.exists():
        shutil.rmtree(INSTALL_BUNDLE)
    version_dir = INSTALL_BUNDLE / "apps" / version
    shutil.copytree(app_dist, version_dir)
    shutil.copytree(launcher_dist, INSTALL_BUNDLE, dirs_exist_ok=True)
    manifest = {
        "schema": 1,
        "kind": "application",
        "id": APP_NAME,
        "version": version,
        "min_app_version": "0.1.0",
        "entrypoint": APP_ENTRYPOINT,
        "files": _inventory(version_dir),
    }
    manifest_path = version_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    current = {
        "schema": 1,
        "version": version,
        "entrypoint": APP_ENTRYPOINT,
        "manifest_sha256": _sha256(manifest_path),
    }
    (INSTALL_BUNDLE / "current.json").write_text(
        json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return INSTALL_BUNDLE


def find_iscc() -> Path | None:
    found = shutil.which("ISCC") or shutil.which("iscc")
    if found:
        return Path(found)
    candidates = [
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe")),
        Path(os.path.expandvars(r"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe")),
        Path(os.path.expandvars(r"%ProgramFiles%\Inno Setup 6\ISCC.exe")),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def compile_installer(iss_path: Path | None = None) -> Path | None:
    target_iss = iss_path or (PROJECT_ROOT / "installer" / "InPhieuHienVat.iss")
    if not target_iss.is_file():
        raise FileNotFoundError(f"Không tìm thấy file Inno Setup script: {target_iss}")
    iscc = find_iscc()
    if iscc is None:
        print("Inno Setup compiler (ISCC.exe) không tìm thấy trên máy tính; bỏ qua bước tạo file Setup.exe.")
        return None
    print(f"Đang biên dịch installer với {iscc}...")
    subprocess.run([str(iscc), str(target_iss)], check=True, cwd=str(PROJECT_ROOT))
    release = _release()
    setup_exe = RELEASE_ARTIFACTS / f"InPhieuHienVat_Setup_{release['version']}.exe"
    if setup_exe.is_file():
        print(f"Đã tạo thành công bộ cài đặt: {setup_exe}")
        return setup_exe
    return None


def package(*, compile_iss: bool = True) -> Path:
    release = _release()
    _validate_inno_version(str(release["version"]))
    app_dist = build_application()
    _smoke_health(app_dist / APP_ENTRYPOINT)
    launcher_dist = build_launcher()
    bundle = assemble_install_bundle(app_dist, launcher_dist)
    _smoke_health(bundle / f"{LAUNCHER_NAME}.exe", app_root=bundle)
    print(f"Đã tạo gói cài đặt: {bundle}")
    if compile_iss:
        compile_installer()
    return bundle


def build_update_package(app_dist: Path, output_path: Path, *, min_app_version: str) -> Path:
    release = _release()
    version = str(release["version"])
    if not SEMVER.fullmatch(min_app_version):
        raise ValueError("min_app_version phải có dạng major.minor.patch")
    _validate_app_dist(app_dist)
    manifest = {
        "schema": 1,
        "kind": "application",
        "id": APP_NAME,
        "version": version,
        "min_app_version": min_app_version,
        "entrypoint": APP_ENTRYPOINT,
        "files": _inventory(app_dist),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            for item in manifest["files"]:
                archive.write(app_dist / Path(str(item["path"])), str(item["path"]))
        os.replace(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output_path


def verify_writable_share(folder: Path) -> None:
    """Verify write access on the target LAN share before publishing."""
    folder.mkdir(parents=True, exist_ok=True)
    probe_name = f".probe_{os.getpid()}_{int(time.time())}.tmp"
    probe_file = folder / probe_name
    try:
        probe_file.write_text("ok", encoding="utf-8")
        if probe_file.read_text(encoding="utf-8") != "ok":
            raise RuntimeError(f"Không thể đọc lại probe file trên LAN: {folder}")
    except Exception as exc:
        raise RuntimeError(f"Không có quyền ghi trên thư mục LAN: {folder}") from exc
    finally:
        probe_file.unlink(missing_ok=True)


def publish_setup(setup_exe: Path, publish_dir: Path) -> Path:
    """Publish Setup installer (.exe) to the LAN software directory using atomic .part copy."""
    if not setup_exe.is_file():
        raise FileNotFoundError(f"Không tìm thấy file Setup để phát hành: {setup_exe}")
    verify_writable_share(publish_dir)
    destination = publish_dir / setup_exe.name
    if destination.is_file():
        if _sha256(destination) == _sha256(setup_exe):
            print(f"Setup {setup_exe.name} đã tồn tại trên LAN với hash trùng khớp; bỏ qua copy.")
            return destination
        raise RuntimeError(f"Setup {setup_exe.name} đã tồn tại trên LAN nhưng khác hash! Dừng để tránh ghi đè artifact lịch sử.")
    setup_part = publish_dir / f"{setup_exe.name}.part"
    try:
        shutil.copyfile(setup_exe, setup_part)
        if _sha256(setup_exe) != _sha256(setup_part) or setup_part.stat().st_size != setup_exe.stat().st_size:
            raise RuntimeError("Hash hoặc kích thước Setup sau khi copy lên LAN không khớp")
        os.replace(setup_part, destination)
        if _sha256(destination) != _sha256(setup_exe):
            raise RuntimeError("Xác minh Setup trên LAN sau khi rename không khớp")
        return destination
    except Exception:
        setup_part.unlink(missing_ok=True)
        raise


def publish_update(package_path: Path, publish_dir: Path, *, notes: str) -> tuple[Path, Path]:
    release = _release()
    if package_path.suffix.casefold() != ".phieuupdate" or not package_path.is_file():
        raise ValueError("Không tìm thấy package .phieuupdate hợp lệ")
    if len(notes) > 2000:
        raise ValueError("Release note dài quá 2000 ký tự")
    verify_writable_share(publish_dir)
    destination = publish_dir / package_path.name
    if destination.is_file():
        if _sha256(destination) != _sha256(package_path):
            raise RuntimeError(f"Package {destination.name} đã tồn tại trên LAN nhưng khác hash! Dừng để tránh ghi đè artifact lịch sử.")
        print(f"Package {package_path.name} đã tồn tại trên LAN với hash trùng khớp.")
    else:
        package_part = publish_dir / f"{package_path.name}.part"
        try:
            shutil.copyfile(package_path, package_part)
            if _sha256(package_path) != _sha256(package_part) or package_part.stat().st_size != package_path.stat().st_size:
                raise RuntimeError("Hash package sau khi copy không khớp")
            os.replace(package_part, destination)
        except Exception:
            package_part.unlink(missing_ok=True)
            raise

    catalog = publish_dir / "latest.json"
    catalog_part = publish_dir / "latest.json.part"
    try:
        payload = {
            "schema": 1,
            "channel": str(release["channel"]),
            "version": str(release["version"]),
            "package": destination.name,
            "sha256": _sha256(destination),
            "size": destination.stat().st_size,
            "notes": notes,
        }
        catalog_part.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(catalog_part, catalog)
        return destination, catalog
    except Exception:
        catalog_part.unlink(missing_ok=True)
        raise


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Đóng gói In Phiếu Hiện Vật")
    parser.add_argument("--build-update", action="store_true")
    parser.add_argument("--min-app-version")
    parser.add_argument("--publish-dir", help="Thư mục phát hành package auto-update (.phieuupdate + latest.json)")
    parser.add_argument("--publish-setup-dir", help="Thư mục phát hành Setup installer (.exe) lên LAN")
    parser.add_argument("--publish-lan", action="store_true", help="Tự động phát hành cả Setup và Update lên các thư mục LAN chuẩn của KDTVN")
    parser.add_argument("--release-notes", default="")
    parser.add_argument("--compile-installer", action="store_true", help="Chỉ chạy bước biên dịch Inno Setup (.iss)")
    parser.add_argument("--no-installer", action="store_true", help="Bỏ qua bước gọi Inno Setup khi đóng gói")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.compile_installer:
        compile_installer()
        return 0
    if not args.build_update:
        bundle = package(compile_iss=not args.no_installer)
        if args.publish_lan or args.publish_setup_dir:
            setup_dir = Path(args.publish_setup_dir or DEFAULT_LAN_SETUP_DIR)
            release = _release()
            setup_exe = RELEASE_ARTIFACTS / f"{APP_NAME}_Setup_{release['version']}.exe"
            if setup_exe.is_file():
                published_setup = publish_setup(setup_exe, setup_dir)
                print(f"Đã phát hành Setup lên LAN: {published_setup}")
        return 0
    if not args.min_app_version:
        raise SystemExit("Thiếu --min-app-version khi tạo update")
    bundle = package(compile_iss=not args.no_installer)
    release = _release()
    output = RELEASE_ARTIFACTS / f"{APP_NAME}-{release['version']}.phieuupdate"
    artifact = build_update_package(APP_DIST, output, min_app_version=args.min_app_version)
    print(f"Đã tạo gói cập nhật: {artifact}")

    update_dir = Path(args.publish_dir or (DEFAULT_LAN_UPDATE_DIR if args.publish_lan else "")) if (args.publish_dir or args.publish_lan) else None
    if update_dir:
        published, catalog = publish_update(artifact, update_dir, notes=args.release_notes)
        print(f"Đã phát hành gói cập nhật: {published}")
        print(f"Đã phát hành catalog: {catalog}")

    setup_dir = Path(args.publish_setup_dir or (DEFAULT_LAN_SETUP_DIR if args.publish_lan else "")) if (args.publish_setup_dir or args.publish_lan) else None
    if setup_dir:
        setup_exe = RELEASE_ARTIFACTS / f"{APP_NAME}_Setup_{release['version']}.exe"
        if not setup_exe.is_file():
            compile_installer()
        if setup_exe.is_file():
            published_setup = publish_setup(setup_exe, setup_dir)
            print(f"Đã phát hành Setup lên LAN: {published_setup}")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())

