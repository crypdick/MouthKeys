import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from mouthkeys.cli import main
from mouthkeys.config import runtime_dir
from mouthkeys.service import request


def test_config_cli_and_doctor(capsys):
    assert main(["config", "language", "auto"]) == 0
    assert json.loads(capsys.readouterr().out)["language"] == "auto"
    assert main(["doctor"]) == 1  # No real desktop is exposed to tests.
    assert json.loads(capsys.readouterr().out)["session"] == "headless"
    assert main(["config", "max_seconds", "zero"]) == 1


def test_desktop_installer_uses_absolute_executable_and_no_autostart_by_default():
    assert main(["install-desktop"]) == 0
    entry = Path(os.environ["XDG_DATA_HOME"]) / "applications/mouthkeys.desktop"
    assert 'Exec="/' in entry.read_text()
    assert not (Path(os.environ["XDG_CONFIG_HOME"]) / "autostart").exists()


def test_real_daemon_ipc_duplicate_start_malformed_request_and_shutdown():
    process = subprocess.Popen(
        [sys.executable, "-m", "mouthkeys", "daemon"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            try:
                result = request("status")
                break
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.03)
        else:
            raise AssertionError("Daemon failed to start")
        assert result["phase"] == "idle"
        duplicate = subprocess.run([sys.executable, "-m", "mouthkeys", "daemon"], timeout=3)
        assert duplicate.returncode == 0
        assert request("status")["phase"] == "idle"
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(2)
            client.connect(str(runtime_dir() / "control.sock"))
            client.sendall(b"not-json\n")
            assert json.loads(client.recv(4096))["ok"] is False
        assert request("history") == []
    finally:
        process.terminate()
        try:
            _, errors = process.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=2)
            raise
    assert process.returncode == 0, errors.decode()
    assert not (runtime_dir() / "control.sock").exists()
