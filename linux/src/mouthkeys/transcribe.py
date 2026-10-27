from pathlib import Path

from .config import Config, cache_dir


def download(model: str):
    from faster_whisper.utils import download_model

    return download_model(model, cache_dir=str(cache_dir() / "models"))


class Transcriber:
    def __init__(self):
        self.key = None
        self.model = None

    def load(self, config: Config):
        key = (config.model, config.device, config.compute_type)
        if key != self.key:
            from faster_whisper import WhisperModel

            self.model = WhisperModel(
                config.model,
                device=config.device,
                compute_type=config.compute_type,
                download_root=str(cache_dir() / "models"),
                local_files_only=True,
            )
            self.key = key

    def transcribe(self, path: Path, config: Config):
        self.load(config)
        segments, _ = self.model.transcribe(
            str(path),
            language=None if config.language == "auto" else config.language,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
