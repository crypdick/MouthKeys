import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def xdg(kind: str, default: str) -> Path:
    return Path(os.environ.get(f"XDG_{kind}_HOME", str(Path.home() / default))) / "mouthkeys"


def state_dir() -> Path:
    return private_dir(xdg("STATE", ".local/state"))


def cache_dir() -> Path:
    return private_dir(xdg("CACHE", ".cache"))


def runtime_dir() -> Path:
    root = os.environ.get("XDG_RUNTIME_DIR")
    return private_dir(Path(root) / "mouthkeys" if root else state_dir() / "run")


def config_path() -> Path:
    return xdg("CONFIG", ".config") / "config.json"


@dataclass(frozen=True)
class Config:
    model: str = "base.en"
    language: str = "en"
    device: str = "cpu"
    compute_type: str = "default"
    audio_source: str = "default"
    delivery: str = "clipboard"
    paste_backend: str = "auto"
    paste_shortcut: str = "ctrl+shift+v"
    max_seconds: int = 300
    audio_budget_mb: int = 4000
    recording_panel: str = "on"

    def validate(self):
        for key, value in asdict(self).items():
            if key not in ("max_seconds", "audio_budget_mb") and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ValueError(f"{key} must be a nonempty string")
        if type(self.max_seconds) is not int or not 1 <= self.max_seconds <= 3600:
            raise ValueError("max_seconds must be between 1 and 3600")
        if type(self.audio_budget_mb) is not int or not 1 <= self.audio_budget_mb <= 1000000:
            raise ValueError("audio_budget_mb must be between 1 and 1000000")
        if self.recording_panel not in ("on", "off"):
            raise ValueError("recording_panel must be on or off")
        if self.delivery not in ("clipboard", "x11"):
            raise ValueError("delivery must be clipboard or x11")
        if self.paste_backend not in ("auto", "xdotool", "wtype", "ydotool"):
            raise ValueError("paste_backend must be auto, xdotool, wtype, or ydotool")
        if self.paste_shortcut not in ("ctrl+v", "ctrl+shift+v"):
            raise ValueError("paste_shortcut must be ctrl+v or ctrl+shift+v")
        if self.device not in ("cpu", "cuda", "auto"):
            raise ValueError("device must be cpu, cuda, or auto")
        return self

    @classmethod
    def load(cls):
        path = config_path()
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text())).validate()

    def save(self):
        self.validate()
        path = config_path()
        private_dir(path.parent)
        # Atomic replacement: a daemon cannot observe a partially written config.
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
            json.dump(asdict(self), file, indent=2)
            temp = Path(file.name)
        temp.replace(path)
