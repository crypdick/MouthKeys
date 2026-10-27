# MouthKeys for Linux

Local dictation for Linux, in the personal [crypdick/MouthKeys](https://github.com/crypdick/MouthKeys)
fork. Record with a desktop shortcut, transcribe on your CPU or NVIDIA GPU, and paste into your
editor or terminal. No account, cloud transcription, telemetry, or update checks.

The Linux runtime is Python/Qt with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
The original Swift/macOS app remains intact. This is an initial Linux implementation, not full
macOS feature parity: no streaming preview, Apple/Parakeet models, media controls, Spoken Send,
or automatic clipboard restoration. The Linux UI provides recording controls, history, copy,
audio reprocessing, model downloads, and settings.

## Install

Python 3.11–3.14, FFmpeg with PulseAudio input, and a PulseAudio server (including PipeWire's
PulseAudio compatibility service) are required. Python 3.13 is the tested version.

On Ubuntu/Debian, install the desktop dependencies:

```sh
sudo apt install ffmpeg wl-clipboard libxcb-cursor0 libxkbcommon-x11-0
# On an X11 session, also install:
sudo apt install xclip xdotool
```

On Fedora the corresponding packages include `ffmpeg-free`, `wl-clipboard`, `xcb-util-cursor`,
`libxkbcommon-x11` and, for X11, `xclip` and `xdotool`. On Arch use `ffmpeg`, `wl-clipboard`,
`xcb-util-cursor`, `libxkbcommon-x11`, and the same X11 tools. Package availability depends on
your distribution's repositories. `mouthkeys doctor` reports missing command-line tools.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```sh
git clone https://github.com/crypdick/MouthKeys.git
cd MouthKeys
uv tool install --python 3.13 './linux[gui]'
mouthkeys install-desktop
mouthkeys download
mouthkeys doctor
mouthkeys gui
```

Ensure `~/.local/bin` is on your PATH (`uv tool update-shell` can configure it). The desktop
launcher contains an absolute executable path. For a terminal-only install, omit `[gui]`.
Models download **only** when you run `mouthkeys download` or press Download selected model.
The default is `base.en` (English), CPU, INT8. Downloads come
from Hugging Face; dictation itself uses cached models with `local_files_only=True`.

## Set up your shortcut

In GNOME **Settings → Keyboard → View and Customize Shortcuts → Custom Shortcuts**, add:

| Name | Command | Example shortcut |
| --- | --- | --- |
| MouthKeys toggle | `/home/YOU/.local/bin/mouthkeys toggle` | Super+Alt+Space |
| MouthKeys cancel | `/home/YOU/.local/bin/mouthkeys cancel` | Super+Alt+Escape |

Replace `/home/YOU` with your actual home directory. Use the output of `command -v mouthkeys`
if installed elsewhere. KDE can bind the same commands under Custom Shortcuts. For Sway:

```text
bindsym $mod+Mod1+space exec ~/.local/bin/mouthkeys toggle
bindsym $mod+Mod1+Escape exec ~/.local/bin/mouthkeys cancel
```

The desktop owns the shortcut, so MouthKeys never grabs global keys or needs root. The first
command starts a private background daemon. `mouthkeys warmup` loads the model ahead of your
first recording; subsequent dictations reuse it. Closing the settings window leaves the daemon
running. Optional login startup: `mouthkeys install-desktop --autostart`. Restart the daemon
after changing desktop session types; its display environment is inherited at launch.

1. Focus your editor or terminal and press the toggle shortcut.
2. Speak, then press it again. The controller shows recording/transcribing/ready status;
   `mouthkeys status` also reports it for a status bar. There are no sounds or pop-up windows.
3. When transcription finishes, paste with Ctrl+V, or Ctrl+Shift+V in most terminals.

Recordings stop automatically after five minutes by default. A busy model rejects additional
recording commands explicitly; it never silently replaces pending work. Cancel suppresses
delivery even if inference has already started. Inference must finish before another recording
can start. Only one model worker runs at a time.

## Text delivery

**Clipboard mode is the default on every desktop.** It writes the finished text to the clipboard
and leaves it there. It replaces your previous clipboard contents; Linux does not yet provide
the macOS version's multi-format clipboard snapshot/restore. Clipboard managers may retain
dictated text. History is saved before delivery, even if the clipboard tool fails.

**X11 optional automatic paste:**

```sh
mouthkeys config delivery x11
# Ctrl+Shift+V is the terminal-oriented default; for ordinary editor/browser fields:
mouthkeys config paste_shortcut ctrl+v
```

The daemon snapshots the focused X window at stop and rechecks before sending the paste
shortcut. If the window changed or cannot be identified, it only copies. It never activates a
window or sends Return. This check cannot distinguish tabs, panes, or fields within the same
X window and is not equivalent to macOS Accessibility validation. Use clipboard mode if you
switch panes while waiting. A `paste_requested` status means the shortcut was sent, not proof
the destination accepted it. Terminal text always uses clipboard paste, never simulated typing.

**Wayland:** native apps cannot be safely targeted with X11 tools. Automatic paste is therefore
disabled, even when `delivery` is set to `x11`. GNOME and KDE work with `wl-copy` plus your
normal paste key. For an explicit “paste last dictation now” desktop shortcut:

```sh
# Sway and other compositors implementing the virtual-keyboard protocol:
mouthkeys config paste_backend wtype
# Or GNOME/KDE, ONLY if you already have a working, user-accessible ydotool daemon:
mouthkeys config paste_backend ydotool
# Bind this to a second desktop shortcut, invoked once transcription is complete:
mouthkeys paste
```

`wtype` does not work on all compositors. `ydotool` requires a separately configured daemon and
access to `/dev/uinput`; MouthKeys neither installs a privileged service nor changes device
permissions. The daemon must inherit `YDOTOOL_SOCKET` if your setup uses a non-default socket.
`paste` copies the last transcript and sends only the configured paste shortcut to the current
focus. Release your shortcut modifiers promptly. Do not invoke it from the GUI while expecting
another app to receive it. Standard manual paste needs neither tool nor extra privileges.

## Models, microphones, and recovery

```sh
# More accurate English model (larger and slower on CPU):
mouthkeys config model small.en
mouthkeys download
mouthkeys warmup
# Multilingual:
mouthkeys config model small
mouthkeys config language auto
mouthkeys download
# CUDA requires compatible NVIDIA/CTranslate2 libraries; see faster-whisper's documentation:
mouthkeys config device cuda
mouthkeys config compute_type float16
# Return to the portable CPU path:
mouthkeys config device cpu
mouthkeys config compute_type int8
# Pick a PulseAudio/PipeWire source (pactl is provided by pulseaudio-utils on Ubuntu):
pactl list short sources
mouthkeys config audio_source YOUR_SOURCE_NAME
```

`default` follows your desktop's default input device. Do not select a `.monitor` source unless
you intentionally want system audio. Change settings only between recordings; a recording
keeps the settings it started with. Use a local CTranslate2 model directory as `model` to avoid
downloads entirely.

```sh
mouthkeys history                     # Latest 100 entries, JSON
mouthkeys copy                        # Latest nonempty transcript
mouthkeys reprocess                   # Latest entry's retained audio
mouthkeys reprocess --id ENTRY_UUID
mouthkeys transcribe recording.wav    # File → stdout; no mic, clipboard, or history writes
mouthkeys clear-history --yes         # Delete all local transcripts and retained recordings
```

History and audio are private files in `$XDG_STATE_HOME/mouthkeys` (normally
`~/.local/state/mouthkeys`). Configuration is in `$XDG_CONFIG_HOME/mouthkeys/config.json`;
models are in `$XDG_CACHE_HOME/mouthkeys/models`. The control socket is user-private under
`$XDG_RUNTIME_DIR/mouthkeys`, falling back to the state directory. Audio for the latest success
and **all failures** is retained for recovery, including after a crash; older successful audio
is removed after a successful dictation. Each reprocess creates a separate attempt, preserving
the original transcript if the retry fails. History and failed audio are not automatically expired:
use Clear history to delete them. No transcript is written to the daemon diagnostic log.

To stop the background service and cancel its current recording, use `mouthkeys shutdown`.
Remove `~/.config/autostart/mouthkeys.desktop` to
disable login startup. Uninstall with `uv tool uninstall mouthkeys-linux` and remove
`~/.local/share/applications/mouthkeys.desktop`. These steps leave history/models intact;
delete the MouthKeys XDG directories separately if you want to erase them.

## Development and validation

```sh
./linux/check.sh                     # Full headless checks and packaging
# Or run the steps individually:
uv sync --project linux --python 3.13 --extra gui --locked
uv run --project linux pytest
uv run --project linux ruff check linux
uv build linux
# Real model smoke check; downloads explicitly, never records or pastes:
uv run --project linux mouthkeys download tiny.en
uv run --project linux python linux/tests/smoke_transcription.py
```

Unit/integration tests use fake microphones and delivery adapters, temporary XDG directories,
and bounded waits. Qt smoke checks use the offscreen backend. Tests never capture live audio,
change the clipboard, synthesize keys, show windows, or play sounds.

Before calling a desktop setup verified, run this manual check:

- Download a model, warm it, choose your actual microphone, and dictate two sentences.
- Paste into an editor and a terminal (Ghostty/c11 where available); confirm Unicode and newlines.
- Cancel a recording; confirm there is no clipboard change or late paste.
- Switch windows while X11 inference runs; confirm it falls back to copy.
- Reprocess retained audio, copy from history, and verify recovery after restarting the daemon.
- Confirm the microphone indicator turns off on stop/cancel and at the maximum duration.

The macOS build and its tests still use Xcode; the Linux runtime does not modify those sources.
