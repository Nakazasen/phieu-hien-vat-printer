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
    _validate_app_dist(root)
    return root


def build_launcher() -> Path:
    icon = PROJECT_ROOT / "app_icon.ico"
    return _run_pyinstaller(
        PROJECT_ROOT / "updater" / "update_launcher.py", LAUNCHER_NAME, add_data=[], console=True, icon=icon
    )


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


def package() -> Path:
    release = _release()
    _validate_inno_version(str(release["version"]))
    app_dist = build_application()
    _smoke_health(app_dist / APP_ENTRYPOINT)
    launcher_dist = build_launcher()
    bundle = assemble_install_bundle(app_dist, launcher_dist)
    _smoke_health(bundle / f"{LAUNCHER_NAME}.exe", app_root=bundle)
    print(f"Đã tạo gói cài đặt: {bundle}")
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


def publish_update(package_path: Path, publish_dir: Path, *, notes: str) -> tuple[Path, Path]:
    release = _release()
    if package_path.suffix.casefold() != ".phieuupdate" or not package_path.is_file():
        raise ValueError("Không tìm thấy package .phieuupdate hợp lệ")
    if len(notes) > 2000:
        raise ValueError("Release note dài quá 2000 ký tự")
    publish_dir.mkdir(parents=True, exist_ok=True)
    destination = publish_dir / package_path.name
    package_part = publish_dir / f"{package_path.name}.part"
    catalog = publish_dir / "latest.json"
    catalog_part = publish_dir / "latest.json.part"
    try:
        shutil.copyfile(package_path, package_part)
        if _sha256(package_path) != _sha256(package_part):
            raise RuntimeError("Hash package sau khi copy không khớp")
        os.replace(package_part, destination)
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
        package_part.unlink(missing_ok=True)
        catalog_part.unlink(missing_ok=True)
        raise


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Đóng gói In Phiếu Hiện Vật")
    parser.add_argument("--build-update", action="store_true")
    parser.add_argument("--min-app-version")
    parser.add_argument("--publish-dir")
    parser.add_argument("--release-notes", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.build_update:
        package()
        return 0
    if not args.min_app_version:
        raise SystemExit("Thiếu --min-app-version khi tạo update")
    release = _release()
    output = RELEASE_ARTIFACTS / f"{APP_NAME}-{release['version']}.phieuupdate"
    artifact = build_update_package(APP_DIST, output, min_app_version=args.min_app_version)
    print(f"Đã tạo gói cập nhật: {artifact}")
    if args.publish_dir:
        published, catalog = publish_update(artifact, Path(args.publish_dir), notes=args.release_notes)
        print(f"Đã phát hành gói: {published}")
        print(f"Đã phát hành catalog: {catalog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
