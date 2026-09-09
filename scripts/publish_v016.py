"""Publish InPhieuHienVat version 0.1.6 to LAN and archive older releases."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import package_app

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def move_to_old(source_file: Path, old_dir: Path):
    old_dir.mkdir(parents=True, exist_ok=True)
    target = old_dir / source_file.name
    print(f"  -> Moving {source_file.name} to old/{source_file.name}...")
    if target.exists():
        if sha256_file(target) == sha256_file(source_file):
            print(f"     [Note] Destination old/{source_file.name} already exists with identical hash. Removing source.")
            source_file.unlink()
            return
        else:
            print(f"     [Warning] Destination old/{source_file.name} exists with different hash. Overwriting.")
            target.unlink()
    shutil.move(str(source_file), str(target))
    print(f"     [OK] Moved to {target}")

def main():
    print("=== BẮT ĐẦU QUY TRÌNH PHÁT HÀNH v0.1.6 & LƯU TRỮ BẢN CŨ VÀO OLD ===")
    
    release_info = package_app._release()
    version = release_info["version"]
    print(f"1. Phiên bản phát hành: {version}")
    assert version == "0.1.6", f"Expected version 0.1.6, got {version}"

    # Build fresh onedir application
    print("2. Đang biên dịch ứng dụng với PyInstaller...")
    app_dist = package_app.build_application()
    package_app._smoke_health(app_dist / package_app.APP_ENTRYPOINT)
    launcher_dist = package_app.build_launcher()
    bundle = package_app.assemble_install_bundle(app_dist, launcher_dist)
    package_app._smoke_health(bundle / f"{package_app.LAUNCHER_NAME}.exe", app_root=bundle)
    print(f"   [OK] Đã tạo gói cài đặt bundle: {bundle}")

    # Build Setup exe
    print("3. Đang biên dịch Inno Setup...")
    setup_exe = package_app.compile_installer()
    assert setup_exe and setup_exe.is_file(), f"Setup exe không tồn tại: {setup_exe}"
    setup_exe_hash = sha256_file(setup_exe)
    setup_exe_size = setup_exe.stat().st_size
    print(f"   [OK] Bộ cài đặt Setup: {setup_exe.name} ({setup_exe_size:,} bytes, sha256: {setup_exe_hash[:12]}...)")

    # Build .phieuupdate package
    update_pkg = package_app.RELEASE_ARTIFACTS / f"{package_app.APP_NAME}-{version}.phieuupdate"
    print(f"4. Đang tạo gói cập nhật: {update_pkg.name}...")
    package_app.build_update_package(app_dist, update_pkg, min_app_version="0.1.0")
    update_pkg_hash = sha256_file(update_pkg)
    update_pkg_size = update_pkg.stat().st_size
    print(f"   [OK] Tạo gói thành công: {update_pkg.name} ({update_pkg_size:,} bytes, sha256: {update_pkg_hash[:12]}...)")

    # Create local latest.json
    release_notes = (
        "0.1.6: Khôi phục ký tự gạch chéo '/' giữa 2 số lượng (vd 20 / 40); "
        "Căn lề chuẩn xác chống xen chữ số; Mở rộng ô đóng dấu Line QC & Part QC (21.4mm x 18.0mm)."
    )
    local_catalog = package_app.RELEASE_ARTIFACTS / "latest.json"
    latest_payload = {
        "schema": 1,
        "channel": str(release_info["channel"]),
        "version": str(version),
        "package": update_pkg.name,
        "sha256": update_pkg_hash,
        "size": update_pkg_size,
        "notes": release_notes,
    }
    local_catalog.write_text(json.dumps(latest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"5. Đã tạo local latest.json: {local_catalog}")

    # Check LAN Directories
    setup_dir = Path(package_app.DEFAULT_LAN_SETUP_DIR)
    update_dir = Path(package_app.DEFAULT_LAN_UPDATE_DIR)
    print(f"6. Kiểm tra quyền ghi trên LAN...")
    package_app.verify_writable_share(setup_dir)
    package_app.verify_writable_share(update_dir)
    print("   [OK] Cả 2 thư mục LAN đều có quyền ghi.")

    # Publish Setup to LAN
    print(f"7. Phát hành Setup v{version} lên LAN...")
    published_setup = package_app.publish_setup(setup_exe, setup_dir, force=True)
    print(f"   [OK] Đã phát hành: {published_setup}")

    # Archive older setup .exe files into setup_dir/old
    print(f"8. Lưu trữ các bản Setup cũ vào thư mục 'old' trên LAN...")
    setup_old_dir = setup_dir / "old"
    for item in list(setup_dir.glob("*.exe")):
        if item.name != setup_exe.name:
            move_to_old(item, setup_old_dir)

    # Publish Update Package and latest.json to LAN
    print(f"9. Phát hành Auto-Update Package & latest.json lên LAN...")
    pub_pkg, pub_catalog = package_app.publish_update(update_pkg, update_dir, notes=release_notes, force=True)
    print(f"   [OK] Đã phát hành package: {pub_pkg}")
    print(f"   [OK] Đã phát hành catalog: {pub_catalog}")

    # Archive older .phieuupdate files into update_dir/old
    print(f"10. Lưu trữ các bản Update cũ vào thư mục 'old' trên LAN...")
    update_old_dir = update_dir / "old"
    for item in list(update_dir.glob("*.phieuupdate")):
        if item.name != update_pkg.name:
            move_to_old(item, update_old_dir)

    # Verification Summary
    print("\n=== BÁO CÁO NGHIỆM THU TRÊN LAN SAU KHI XUẤT BẢN ===")
    print("\n[Thư mục Cài đặt - SETUP_DIR]:")
    print(f"Path: {setup_dir}")
    for p in sorted(setup_dir.iterdir()):
        if p.is_file():
            print(f"  - File: {p.name} ({p.stat().st_size:,} bytes)")
        elif p.is_dir():
            print(f"  - Dir:  {p.name}/")
    print("\n[Thư mục Cài đặt Cũ - SETUP_DIR/old]:")
    for p in sorted(setup_old_dir.iterdir()):
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")

    print("\n[Thư mục Tự cập nhật - UPDATE_DIR]:")
    print(f"Path: {update_dir}")
    for p in sorted(update_dir.iterdir()):
        if p.is_file():
            print(f"  - File: {p.name} ({p.stat().st_size:,} bytes)")
        elif p.is_dir():
            print(f"  - Dir:  {p.name}/")
    print("\n[Thư mục Cập nhật Cũ - UPDATE_DIR/old]:")
    for p in sorted(update_old_dir.iterdir()):
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")

    # Integrity verification
    lan_setup_hash = sha256_file(setup_dir / setup_exe.name)
    lan_update_hash = sha256_file(update_dir / update_pkg.name)
    assert lan_setup_hash == setup_exe_hash, "Lỗi: Hash Setup trên LAN không khớp local!"
    assert lan_update_hash == update_pkg_hash, "Lỗi: Hash Package trên LAN không khớp local!"

    lan_catalog_content = json.loads((update_dir / "latest.json").read_text(encoding="utf-8"))
    assert lan_catalog_content["version"] == "0.1.6", "Lỗi: Version trong latest.json trên LAN không phải 0.1.6"
    assert lan_catalog_content["package"] == update_pkg.name, "Lỗi: Package trong latest.json không khớp"
    assert lan_catalog_content["sha256"] == update_pkg_hash, "Lỗi: Hash trong latest.json không khớp"

    print("\n[XÁC NHẬN TOÀN VẸN 100%]")
    print(f"  Setup SHA-256:   {lan_setup_hash}")
    print(f"  Update SHA-256:  {lan_update_hash}")
    print(f"  Catalog Version: {lan_catalog_content['version']}")
    print(f"  Catalog Package: {lan_catalog_content['package']}")
    print(f"  Catalog Notes:    {lan_catalog_content['notes']}")
    print("\n>>> QUY TRÌNH PHÁT HÀNH v0.1.6 VÀ DI CHUYỂN BẢN CŨ THÀNH CÔNG RỰC RỠ! <<<")

if __name__ == "__main__":
    main()

