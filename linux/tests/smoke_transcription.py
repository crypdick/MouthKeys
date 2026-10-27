"""Explicit opt-in real ASR smoke test. Run after `mouthkeys download tiny.en`."""

from pathlib import Path

from mouthkeys.config import Config
from mouthkeys.transcribe import Transcriber

fixture = (
    Path(__file__).resolve().parents[2]
    / "Tests/FluidDictationIntegrationTests"
    / "Resources/dictation_fixture.wav"
)
text = Transcriber().transcribe(fixture, Config(model="tiny.en"))
print(text)
assert "hello" in text.lower(), f"Expected greeting in fixture transcription: {text!r}"
