import os
import shutil
import subprocess
import time

from .config import Config


def session():
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
        return "wayland"
    return "x11" if os.environ.get("DISPLAY") else "headless"


def run(args, **kwargs):
    try:
        return subprocess.run(args, check=True, timeout=3, capture_output=True, **kwargs)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Install {args[0]} (see linux/README.md)") from exc
    except subprocess.CalledProcessError as exc:
        detail = (
            exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
        )
        raise RuntimeError(f"{args[0]} failed: {(detail or '').strip()}") from exc


class Delivery:
    def focus(self):
        if session() != "x11":
            return None
        try:
            return run(["xdotool", "getwindowfocus"]).stdout.decode().strip() or None
        except (RuntimeError, subprocess.TimeoutExpired):
            return None

    def copy(self, text: str):
        if session() == "wayland":
            # wl-copy forks to own the selection; never use --paste-once (XWayland reads twice).
            run(["wl-copy", "--type", "text/plain;charset=utf-8"], input=text.encode())
        elif session() == "x11":
            # xclip's selection owner inherits stdout unless redirected; do not capture it.
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-in"],
                    input=text.encode(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=3,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("Install xclip (see linux/README.md)") from exc
        else:
            raise RuntimeError("No desktop session; transcript saved in history")

    def paste_key(self, config: Config):
        backend = config.paste_backend
        if backend == "auto":
            if session() != "x11":
                raise ValueError("Wayland: use your normal paste key, or configure wtype/ydotool")
            backend = "xdotool"
        shifted = config.paste_shortcut == "ctrl+shift+v"
        if backend == "xdotool":
            if session() != "x11":
                raise ValueError("xdotool cannot paste into native Wayland apps")
            run(["xdotool", "key", "--clearmodifiers", config.paste_shortcut])
        elif backend == "wtype":
            args = ["wtype", "-M", "ctrl"]
            if shifted:
                args += ["-M", "shift"]
            args += ["-k", "v"]
            if shifted:
                args += ["-m", "shift"]
            run(args + ["-m", "ctrl"])
        else:
            keys = ["29:1"] + (["42:1"] if shifted else []) + ["47:1", "47:0"]
            run(["ydotool", "key", *keys, *(["42:0"] if shifted else []), "29:0"])

    def deliver(self, text: str, config: Config, target: str | None):
        self.copy(text)
        if config.delivery != "x11":
            return "copied"
        if session() != "x11" or target is None or self.focus() != target:
            return "copied"
        # Let the selection owner become ready, then recheck without activating any window.
        time.sleep(0.15)
        if self.focus() != target:
            return "copied"
        self.paste_key(config)
        return "paste_requested"  # Key injection cannot prove the destination consumed the text.


def doctor(config: Config):
    desktop = session()
    required = ["ffmpeg"]
    if desktop == "wayland":
        required += ["wl-copy"]
    elif desktop == "x11":
        required += ["xclip"]
        if config.delivery == "x11" or config.paste_backend in ("auto", "xdotool"):
            required += ["xdotool"]
    if config.paste_backend in ("wtype", "ydotool"):
        required += [config.paste_backend]
    return {
        "session": desktop,
        "commands": {name: shutil.which(name) for name in required},
        "audio_source": config.audio_source,
        "model": config.model,
        "delivery": config.delivery,
    }
