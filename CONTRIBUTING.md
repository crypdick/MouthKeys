# Contributing

MouthKeys for Linux focuses on reliable local dictation, shortcuts, audio capture, text delivery,
and a small Qt interface.

For bugs, include your distribution, desktop/compositor and version, Wayland or X11 session,
Python version, selected speech model/device, destination application, and exact reproduction
steps. Include `mouthkeys doctor` and `mouthkeys status` output when useful. Remove private
transcripts, microphone names, paths, and other sensitive details before sharing diagnostics.

Run `./linux/check.sh` before a PR. Tests must remain headless and use fake capture, clipboard,
and key adapters with isolated XDG directories. Never record real audio, modify a real clipboard,
synthesize keys, show windows, or play sounds in tests. Real desktop checks are listed in
[linux/README.md](linux/README.md#development-and-validation).

Target `crypdick/MouthKeys`, base `main`. Describe the concrete behavior change, validation,
and remaining desktop limitations. Include screenshots for visible UI changes when possible.

Keep telemetry, cloud transcription, and update checks out. Model downloads must remain explicit.
Credit upstream contributions as described in [UPSTREAM.md](UPSTREAM.md).
Contributions are licensed under GPL-3.0.
