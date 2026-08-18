"""Stable launcher for versioned In Phiếu Hiện Vật application bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
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


class LauncherStateError(ValueError):
    """Raised when current.json cannot safely identify an application version."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LauncherStateError(f"Không đọc được trạng thái launcher: {path}") from exc
    if not isinstance(value, dict):
        raise LauncherStateError(f"Trạng thái launcher không hợp lệ: {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_entrypoint(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if not text or text.startswith("/") or ".." in text.split("/") or ":" in text:
        raise LauncherStateError(f"Entrypoint không an toàn: {value}")
    if not text.casefold().endswith(".exe"):
        raise LauncherStateError("Entrypoint phải là file .exe")
    return text


def resolve_current_entrypoint(app_root: str | os.PathLike[str]) -> Path:
    root = Path(app_root).resolve()
    state = _read_json(root / "current.json")
    version = str(state.get("version", ""))
    version_dir = (root / "apps" / version).resolve()
    if root not in version_dir.parents:
        raise LauncherStateError("Version đang kích hoạt không an toàn")
    manifest_path = version_dir / "manifest.json"
    if not manifest_path.is_file() or _sha256_file(manifest_path) != state.get("manifest_sha256"):
        raise LauncherStateError("Manifest của version đang kích hoạt bị thiếu hoặc đã thay đổi")
    entrypoint = (version_dir / _safe_entrypoint(state.get("entrypoint"))).resolve()
    if version_dir not in entrypoint.parents or not entrypoint.is_file():
        raise LauncherStateError("Không tìm thấy executable của version đang kích hoạt")
    return entrypoint


def default_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent / "release_artifacts" / "install_bundle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Khởi chạy In Phiếu Hiện Vật")
    parser.add_argument("--app-root", default=str(default_app_root()))
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("app_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    app_args = args.app_args[1:] if args.app_args[:1] == ["--"] else args.app_args
    try:
        executable = resolve_current_entrypoint(args.app_root)
        if args.health_check:
            completed = subprocess.run(
                [str(executable), "--health-check", *app_args],
                cwd=str(executable.parent),
                timeout=180,
                check=False,
            )
            return completed.returncode
        subprocess.Popen([str(executable), *app_args], cwd=str(executable.parent))
    except (LauncherStateError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"Không thể khởi chạy In Phiếu Hiện Vật: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
