# Security

Report vulnerabilities privately through this repository's GitHub Security tab when private
vulnerability reporting is available. Otherwise contact the maintainer privately before posting
sensitive reproduction details. Include the Linux distribution, desktop/session, commit, and steps.

Dictation runs locally. There is no account, telemetry, crash reporting, cloud transcription,
or automatic update check. Model downloads contact Hugging Face only when explicitly requested.

History and recovery audio live under `$XDG_STATE_HOME/mouthkeys` (normally
`~/.local/state/mouthkeys`), configuration under `$XDG_CONFIG_HOME/mouthkeys`, and cached models
under `$XDG_CACHE_HOME/mouthkeys`. The control socket is user-private. Clipboard managers may
retain dictated text; consult the [Linux guide](linux/README.md#text-delivery) for delivery limits.

In scope: exposures of audio, transcripts, clipboard contents, unsafe imports, and abuse of
MouthKeys' local control interface. Report OS and third-party dependency vulnerabilities to their
maintainers as well, and tell us if a pinned dependency needs updating.
