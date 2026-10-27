import os
import subprocess
import sys
import time

import pytest


@pytest.mark.parametrize("crash", [False, True])
def test_capture_lifeline_stops_child_on_stop_or_daemon_death(tmp_path, crash):
    ready, stopped = tmp_path / "ready", tmp_path / "stopped"
    capture_script = tmp_path / "fake_capture.py"
    capture_script.write_text(
        "import signal, time\nfrom pathlib import Path\n"
        f"def stop(*_):\n    Path({str(stopped)!r}).touch()\n    raise SystemExit(0)\n"
        "signal.signal(signal.SIGINT, stop)\n"
        f"Path({str(ready)!r}).touch()\n"
        "while True: time.sleep(0.1)\n"
    )
    # Stand-in daemon owns only the lifeline; no capture device is opened.
    parent_script = tmp_path / "fake_daemon.py"
    parent_script.write_text(
        "import subprocess, sys\n"
        f"p = subprocess.Popen([sys.executable, '-m', 'mouthkeys.capture', "
        f"sys.executable, {str(capture_script)!r}], stdin=subprocess.PIPE)\n"
        "sys.stdin.buffer.read(1)\n"
        "p.stdin.close()\np.wait(timeout=4)\n"
    )
    parent = subprocess.Popen([sys.executable, str(parent_script)], stdin=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 3
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.exists(), "Fake capture did not start"
        if crash:
            parent.kill()
        else:
            parent.stdin.close()
        parent.wait(timeout=4)
        deadline = time.monotonic() + 3
        while not stopped.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert stopped.exists(), "Capture survived loss of daemon lifeline"
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=2)
        if not parent.stdin.closed:
            parent.stdin.close()


def test_recorder_uses_supervised_ffmpeg_and_finishes_wav(monkeypatch, tmp_path):
    from mouthkeys.audio import Recorder
    from mouthkeys.config import Config

    class FakeProcess:
        def __init__(self, args, **kwargs):
            assert args[1:5] == ["-P", "-m", "mouthkeys.capture", "ffmpeg"]
            assert args[args.index("-f") + 1] == "pulse"
            before_input = args[: args.index("-i")]
            assert before_input[before_input.index("-sample_rate") + 1] == "16000"
            assert before_input[before_input.index("-channels") + 1] == "1"
            assert before_input[before_input.index("-fragment_size") + 1] == "640"
            assert kwargs["stdin"] == subprocess.PIPE
            assert kwargs["start_new_session"]
            self.stdin = open(os.devnull, "wb")
            self.pid = 999999

        def poll(self):
            return None

        def wait(self, timeout):
            assert self.stdin.closed
            return 255

    monkeypatch.setattr(subprocess, "Popen", FakeProcess)
    recorder = Recorder(Config(), tmp_path / "recording.wav")
    recorder.stop()
    assert recorder.errors.closed
