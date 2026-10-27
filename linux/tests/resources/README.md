# Dictation audio fixture

`dictation_fixture.wav` is the deterministic speech sample used by
`../smoke_transcription.py`. It is retained from upstream MouthKeys' integration tests under
the repository's GPL-3.0 license. Expected greeting: “hello fluid voice”.

Replacement samples must be redistributable WAV, mono, 16 kHz, 16-bit PCM, roughly 2–4 seconds,
and include “hello”. This fixture is transcribed from disk; tests never record a microphone.
