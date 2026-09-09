import subprocess
import sys
import pytest
from ui.main_window import _is_pid_alive, _wait_for_process_exit


def test_is_pid_alive_on_nonexistent_pid():
    # Must return False without raising WinError 6 or WinError 87
    assert _is_pid_alive(999999) is False


def test_wait_for_process_exit_on_nonexistent_pid():
    # Must return cleanly without raising WinError 6 or WinError 87
    _wait_for_process_exit(999999, timeout_seconds=1.0)


def test_wait_for_process_exit_on_terminating_process():
    # Spawn a fast child process
    proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(0.3)'])
    pid = proc.pid
    assert _is_pid_alive(pid) is True
    # Wait for it to exit
    _wait_for_process_exit(pid, timeout_seconds=5.0)
    assert _is_pid_alive(pid) is False
