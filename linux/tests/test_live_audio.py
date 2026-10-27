import struct
import wave

import numpy as np

from mouthkeys.audio import live_levels, read_live_audio
from mouthkeys.transcribe import Transcriber


def test_unfinished_wav_preview_reads_bounded_tail(tmp_path):
    path = tmp_path / "live.wav"
    samples = np.arange(25 * 16000, dtype=np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(samples.tobytes())
    # The same unfinished RIFF/data lengths FFmpeg writes while recording.
    with path.open("r+b") as file:
        file.seek(4)
        file.write(struct.pack("<I", 0xFFFFFFFF))
        file.seek(40)
        file.write(struct.pack("<I", 0xFFFFFFFF))
    audio = read_live_audio(path)
    assert len(audio) == 20 * 16000
    np.testing.assert_array_equal(audio, samples[-20 * 16000 :].astype(np.float32) / 32768)
    levels = live_levels(path)
    assert len(levels) == 63
    assert all(0 <= value <= 1 for value in levels)
    engine = Transcriber()
    engine._decode = lambda audio, config: str(len(audio))
    assert engine.preview(path, None) == "320000"
