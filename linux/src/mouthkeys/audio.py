import os
import signal
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

from .config import Config


class Recorder:
    def __init__(self, config: Config, path: Path):
        self.errors = tempfile.TemporaryFile()
        self.process = None
        try:
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "mouthkeys.capture",
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-y",
                    "-f",
                    "pulse",
                    "-i",
                    config.audio_source,
                    "-t",
                    str(config.max_seconds),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(path),
                ],
                # EOF is a lifeline: even SIGKILL of the daemon closes this pipe.
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=self.errors,
                start_new_session=True,
            )
            time.sleep(0.15)
            if self.process.poll() is not None:
                raise RuntimeError(self.error() or "Microphone capture failed")
        except BaseException:
            if self.process is not None:
                self.process.stdin.close()
                self.process.wait(timeout=3)
            self.errors.close()
            raise

    def error(self):
        self.errors.seek(0)
        return self.errors.read(4096).decode(errors="replace").strip()

    def finished(self):
        return self.process.poll() is not None

    def stop(self):
        self.process.stdin.close()
        try:
            code = self.process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=3)
            raise RuntimeError("Microphone did not stop; saved audio may need recovery") from None
        finally:
            error = self.error()
            self.errors.close()
        # FFmpeg returns 255 after a clean SIGINT, and 0 at the duration limit.
        if code not in (0, 255):
            raise RuntimeError(error or f"Microphone capture exited with status {code}")


def check_audio(path: Path):
    with wave.open(str(path), "rb") as wav:
        if wav.getnframes() < 1600:
            raise ValueError("Recording is too short; speak for at least a moment")
