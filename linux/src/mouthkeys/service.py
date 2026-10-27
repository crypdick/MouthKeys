import fcntl
import json
import os
import shutil
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
import uuid

from .audio import Recorder, check_audio
from .config import Config, runtime_dir, state_dir
from .delivery import Delivery
from .storage import History
from .transcribe import Transcriber

MAX_MESSAGE = 1024 * 1024


class Controller:
    def __init__(self, history=None, transcriber=None, delivery=None, recorder=Recorder):
        self.history = history or History()
        self.history.recover()
        self.transcriber = transcriber or Transcriber()
        self.delivery = delivery or Delivery()
        self.recorder_factory = recorder
        self.lock = threading.RLock()
        self.phase = "idle"
        self.message = "Ready"
        self.item_id = None
        self.recorder = None
        self.cancelled = False
        self.started = None
        self.worker = None

    def status(self):
        with self.lock:
            return {
                "phase": self.phase,
                "message": self.message,
                "id": self.item_id,
                "seconds": round(time.monotonic() - self.started, 1) if self.started else 0,
            }

    def command(self, action, **data):
        with self.lock:
            if action == "status":
                return self.status()
            if action == "history":
                return self.history.rows()
            if action == "toggle":
                action = "stop" if self.phase == "recording" else "start"
            if action == "cancel":
                self.cancelled = True
                if self.phase == "recording":
                    try:
                        self.recorder.stop()
                    finally:
                        self.recorder = None
                        self.history.recording(self.item_id).unlink(missing_ok=True)
                        self.history.update(self.item_id, "cancelled")
                        self.phase, self.message, self.started = "idle", "Cancelled", None
                elif self.phase in ("transcribing", "loading"):
                    self.message = "Cancelling; waiting for model to finish"
                return self.status()
            if action == "stop":
                if self.phase != "recording":
                    raise ValueError("Not recording")
                # Freeze configuration and destination at stop, before model work.
                target = self.delivery.focus() if self.config.delivery == "x11" else None
                try:
                    self.recorder.stop()
                except Exception as exc:
                    self.history.update(self.item_id, "failed", error=str(exc))
                    self.phase, self.message, self.started = "idle", str(exc), None
                    raise
                finally:
                    self.recorder = None
                self._transcribe(target)
                return self.status()
            if self.phase != "idle":
                raise ValueError(f"Busy ({self.phase}); wait or cancel before {action}")
            if action == "start":
                self.config = Config.load()
                self.item_id = str(uuid.uuid4())
                self.cancelled = False
                self.history.begin(self.item_id)
                try:
                    self.recorder = self.recorder_factory(
                        self.config, self.history.recording(self.item_id)
                    )
                except Exception as exc:
                    self.history.update(self.item_id, "failed", error=str(exc))
                    self.message = str(exc)
                    raise
                self.phase, self.message = "recording", "Listening — toggle again to finish"
                self.started = time.monotonic()
                return self.status()
            if action == "reprocess":
                item_id = data.get("id") or self.item_id
                if not item_id:
                    rows = self.history.rows()
                    item_id = rows[0]["id"] if rows else None
                if not item_id or not self.history.recording(item_id).exists():
                    raise ValueError("No retained audio for this entry")
                self.config = Config.load()
                # A retry is a new attempt: failure/cancellation must not erase the original.
                retry_id = str(uuid.uuid4())
                shutil.copyfile(self.history.recording(item_id), self.history.recording(retry_id))
                self.history.begin(retry_id)
                self.item_id = retry_id
                self.cancelled = False
                self._transcribe(None)  # Reprocessing never pastes into an old destination.
                return self.status()
            if action == "warmup":
                self.config = Config.load()
                self.cancelled = False
                self.phase, self.message = "loading", "Loading local model"
                self.worker = threading.Thread(target=self._warmup, daemon=True)
                self.worker.start()
                return self.status()
            if action in ("copy", "paste"):
                text = self.history.latest_text()
                if data.get("id"):
                    text = next(
                        (row["text"] for row in self.history.rows() if row["id"] == data["id"]), ""
                    )
                    if not text:
                        raise ValueError("No transcript for this entry")
                self.delivery.copy(text)
                if action == "paste":
                    # Explicit user shortcut: paste now, into the currently focused app.
                    time.sleep(0.2)
                    self.delivery.paste_key(Config.load())
                self.message = "Copied" if action == "copy" else "Paste requested"
                return self.status()
            if action == "clear":
                self.history.clear()
                self.item_id = None
                self.message = "History and recordings cleared"
                return self.status()
            raise ValueError(f"Unknown command: {action}")

    def _warmup(self):
        try:
            self.transcriber.load(self.config)
            message = "Model ready"
        except Exception as exc:
            message = f"Model unavailable: {exc}. Run mouthkeys download first."
        with self.lock:
            self.phase, self.message = "idle", "Cancelled" if self.cancelled else message

    def _transcribe(self, target):
        self.phase, self.message = "transcribing", "Transcribing locally"
        self.started = None
        self.history.update(self.item_id, "transcribing")
        self.worker = threading.Thread(target=self._finish, args=(target,), daemon=True)
        self.worker.start()

    def _finish(self, target):
        text = ""
        try:
            path = self.history.recording(self.item_id)
            check_audio(path)
            text = self.transcriber.transcribe(path, self.config)
            with self.lock:
                if self.cancelled:
                    self.history.update(self.item_id, "cancelled")
                    path.unlink(missing_ok=True)
                    self.message = "Cancelled"
                elif not text:
                    self.history.update(self.item_id, "failed", error="No speech detected")
                    self.message = "No speech detected; audio retained for reprocessing"
                else:
                    # Persist before any clipboard/keyboard work so delivery failures lose no words.
                    self.history.update(self.item_id, "transcribed", text)
                    result = self.delivery.deliver(text, self.config, target)
                    self.history.update(self.item_id, result, text)
                    self.history.prune_audio(self.item_id)
                    self.message = (
                        "Copied — paste into your app"
                        if result == "copied"
                        else "Paste requested — transcript also on clipboard"
                    )
        except Exception as exc:
            with self.lock:
                if self.cancelled:
                    self.history.update(self.item_id, "cancelled")
                    self.history.recording(self.item_id).unlink(missing_ok=True)
                    self.message = "Cancelled"
                else:
                    self.history.update(self.item_id, "failed", text, str(exc))
                    self.message = f"{exc}. Saved in history; audio retained for reprocessing."
        finally:
            with self.lock:
                self.phase = "idle"

    def tick(self):
        with self.lock:
            if self.phase == "recording" and (
                self.recorder.finished()
                or time.monotonic() - self.started >= self.config.max_seconds
            ):
                try:
                    self.command("stop")
                except Exception:
                    pass  # The stop path has already persisted the error for the UI.


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        try:
            line = self.rfile.readline(MAX_MESSAGE + 1)
            if len(line) > MAX_MESSAGE or not line.endswith(b"\n"):
                raise ValueError("Request too large or incomplete")
            data = json.loads(line)
            action = data.pop("action")
            if action == "shutdown":
                result = self.server.controller.command("cancel")
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                result = self.server.controller.command(action, **data)
            response = {"ok": True, "result": result}
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}
        try:
            self.wfile.write(json.dumps(response).encode() + b"\n")
        except (BrokenPipeError, ConnectionResetError):
            pass


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def service_actions(self):
        self.controller.tick()


def serve():
    os.umask(0o077)
    root = runtime_dir()
    with (root / "daemon.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # Another launcher won the startup race.
        path = root / "control.sock"
        path.unlink(missing_ok=True)
        controller = Controller()
        with Server(str(path), Handler) as server:
            server.controller = controller

            def shutdown(*_):
                controller.command("cancel")
                threading.Thread(target=server.shutdown, daemon=True).start()

            signal.signal(signal.SIGTERM, shutdown)
            signal.signal(signal.SIGINT, shutdown)
            try:
                server.serve_forever(poll_interval=0.1)
            finally:
                path.unlink(missing_ok=True)


def request(action, **data):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect(str(runtime_dir() / "control.sock"))
        sock.sendall(json.dumps({"action": action, **data}).encode() + b"\n")
        with sock.makefile("rb") as stream:
            line = stream.readline(MAX_MESSAGE + 1)
        if len(line) > MAX_MESSAGE:
            raise RuntimeError("Response too large")
        result = json.loads(line)
        if not result["ok"]:
            raise RuntimeError(result["error"])
        return result["result"]


def ensure_daemon():
    try:
        request("status")
        return
    except (FileNotFoundError, ConnectionRefusedError):
        pass
    log = state_dir() / "daemon.log"
    with log.open("a") as output:
        log.chmod(0o600)
        subprocess.Popen(
            [sys.executable, "-m", "mouthkeys", "daemon"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            start_new_session=True,
        )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            request("status")
            return
        except (FileNotFoundError, ConnectionRefusedError):
            time.sleep(0.05)
    raise RuntimeError(f"Daemon did not start; see {log}")
