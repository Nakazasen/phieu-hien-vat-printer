from __future__ import annotations

from package_app import main as package_main


def main() -> None:
    """Backward-compatible build entrypoint for the versioned onedir bundle."""
    package_main()


if __name__ == "__main__":
    main()
