from __future__ import annotations

import argparse
import sys

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

from ui.main_window import SlipPrinterApp, _wait_for_process_exit, run_health_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--wait-for-pid", type=int)
    args, _unknown = parser.parse_known_args(argv)
    if args.health_check:
        run_health_check()
        return 0
    if args.wait_for_pid is not None:
        _wait_for_process_exit(args.wait_for_pid)
    app = SlipPrinterApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
