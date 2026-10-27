# MouthKeys

> **Personal Linux fork:** [crypdick/MouthKeys](https://github.com/crypdick/MouthKeys) adds a
> Linux runtime with local Whisper transcription, desktop shortcuts, and history/settings UI.
> **[Linux installation and usage →](linux/README.md)**. The macOS app and its upstream
> documentation continue below; the DMG is macOS-only.

<p align="center"><b><i>Wicked fast voice to text for macOS: no frills, just function, well designed</i></b></p>

<p align="center"><img src="docs/images/overlay.png" width="560" alt="The MouthKeys overlay mid-dictation: the live transcript above a voice trace, a 13-second timer, 43 words and 203 words per minute in the foot row, and the active mic. History and copy sit on the left rail, cancel and reprocess on the right."></p>

<p align="center"><sub>mid-dictation: the live transcript, your voice as a trace, and the word count and words per minute as you speak.</sub></p>

<p align="center"><a href="https://github.com/BenevolentFutures/MouthKeys/releases/latest/download/MouthKeys.dmg"><img src="https://img.shields.io/github/v/release/BenevolentFutures/MouthKeys?style=for-the-badge&label=download%20MouthKeys.dmg&labelColor=111111&color=FF4F1F" height="36" alt="download MouthKeys.dmg, the latest release"></a></p>

<p align="center">free and open source · macOS 15 or later · made for Apple Silicon · <a href="https://mouthkeys.com">mouthkeys.com</a> · <a href="docs/BUILDING.md">build from source</a></p>

---

listen.

you talk to your computer all day now. prompts for agents, replies, notes. dictation should be the fastest way in, but it fails quietly. the text lands in the wrong window. a terminal swallows it. the clipboard you were holding is gone. you find out when you look up.

the problem is not hearing you. the problem is. delivery.

**MouthKeys is on-device dictation for macOS.** hold or tap a hotkey, speak, and the text lands where you were typing when you stopped. the speech model runs on your Mac: Parakeet, Nemotron, Cohere Transcribe, Whisper or Apple Speech. no account, no telemetry, no subscription. when it sees a paste fail, it tells you and puts the words on your clipboard.

## what you get.

- **paste you can trust.** when a paste fails in a way the app can detect, a card shows, and the text goes on your clipboard unless you copied something since. your own clipboard comes back, images and files included. back-to-back dictations queue instead of dropping. [#4], [`8ab26a8`][8ab26a8]
- **a faster stop.** in a headless benchmark with a 13,600-entry history, stop-path work outside the model fell from a 145 ms median to 4 ms; model time is unchanged. a stalled model no longer loses the recording: it is kept for Reprocess, even across a restart. [#9], [#10]
- **built for terminals.** Ghostty and [c11](https://github.com/Stage-11-Agentics/c11), Stage 11's terminal multiplexer, always get Reliable Paste. upstream forces Ghostty; we added c11. [`8ed75b9`][8ed75b9]
- **Spoken Send.** end with "send it" (or any phrase you pick, like "send send") and Return follows the text half a second later. upstream blocks terminals; we send in every app, only to the pane or field you stopped in. off by default. [#7], [#8]
- **Q for a question mark.** end with "Q", or say "Q Q" anywhere, and it types "?". off by default.
- **a live voice trace.** a scrolling trace of your voice, calibrated to the recording, so you can see it hearing you. [#22], [#24]
- **live counters.** a timer, a word count and words per minute while you speak. [#27]
- **your mic at a glance.** the active mic shows in the overlay, with the battery level of a Hollyland lapel mic. [#29], [#30]
- **a history browser.** recent dictations, each one click from copy or reprocess. drag the overlay anywhere. [#25]
- **an interface that stays quiet.** the overlay, history, cards, menu bar and icon share one visual language, Datasheet Mono: square, flat, monochrome, with orange marking only what is live. copy, reprocess, cancel and history sit one click away on a slim rail beside the pill, and nothing on screen moves unless it means something. [#17], [design notes](design/visual-language/DESIGN.md)
- **hotkey, mic and media fixes.** holds that always end, removed mics that stay removed, media resumed only if we paused it, a hung mic routed around, and a hotkey to reprocess the last dictation. [#2], [`8295536`][8295536], [`68afebc`][68afebc], [`0e2948a`][0e2948a]

<p align="center"><img src="docs/images/history.png" width="520" alt="The MouthKeys history browser open directly above the recording overlay: recent dictations newest first, each with its time, word count and destination app. Below it, the overlay is mid-dictation with its live transcript, voice trace, timer and counters."></p>

<p align="center"><sub>the history browser opens right where you are, above the overlay. click a dictation to insert it again.</sub></p>

## install.

### download.

1. **[download MouthKeys.dmg](https://github.com/BenevolentFutures/MouthKeys/releases/latest/download/MouthKeys.dmg)**, the latest release.
2. open it and drag MouthKeys to Applications.
3. open MouthKeys. it walks you through the rest: Microphone, Accessibility and a speech model.

that's the whole install. you don't need to clone this repo, install Xcode or build anything. the app is signed with a Developer ID and notarized by Apple, so it opens like any other app.

it runs on macOS 15 or later. Parakeet, Nemotron and Cohere, the default engines, need Apple Silicon. Apple Speech needs macOS 26. Whisper up to Medium and Apple ASR Legacy, the older Apple engine, also run on Intel, which this fork has not tested.

**updating.** the app does not update itself. download the new DMG and drag MouthKeys over the old one; your settings, dictionary, history and permissions stay.

### build it yourself.

the code is all here, and you're welcome to build your own. it takes Xcode 26 and, ideally, a free Apple Account for signing:

```bash
git clone https://github.com/BenevolentFutures/MouthKeys.git
cd MouthKeys
./build.sh
```

[docs/BUILDING.md](docs/BUILDING.md) walks you through it: what to install, signing, a dev build that runs beside the downloaded app, installing your own build in its place, and what to do if the hotkeys go quiet.

### first launch.

**permissions.** Microphone, to hear you. Accessibility, to type into other apps. Apple ASR Legacy also asks for Speech Recognition. then pick a speech model; the default on Apple Silicon, Parakeet TDT v3, is about a 460 MiB download.

**coming from 0.1.0.** from 0.1.1 MouthKeys has its own bundle ID. on its first launch it copies your settings, dictionary and history from 0.1.0 once and leaves the old copy untouched. macOS sees a new app, so it asks for Microphone and Accessibility again.

**coming from FluidVoice.** stock FluidVoice and the earliest builds of this fork share the bundle ID `com.FluidApp.app`. if you have used either on this Mac, MouthKeys copies its settings, dictionary and history once, on first launch, and never changes the original. after that the two apps keep separate data and can run side by side. macOS does not carry permissions over, so you grant them again.

## privacy.

no telemetry, no account. your audio and your text stay on your Mac unless you choose otherwise. the app goes online for three things, each your choice:

- downloading the speech model you pick.
- AI cleanup, if you set up a provider: OpenAI, Anthropic, Google, xAI, Groq, Cerebras, OpenRouter or a custom endpoint. Ollama and LM Studio stay on your Mac.
- **Apple ASR Legacy**, which lets macOS choose where speech is recognized, and that may be Apple's servers. every other engine runs on the Mac.

Feedback opens a draft GitHub issue in your browser. the app posts nothing; you read it and submit it yourself.

## built on FluidVoice.

MouthKeys is a fork of [FluidVoice](https://github.com/altic-dev/FluidVoice) by altic-dev, taken on 2026-08-15 at upstream [`d62adc9`][base]. FluidVoice did the hard part: the speech pipeline, the model integrations, hotkeys, typing into other apps, settings and model downloads.

**why we forked.** we dictate into coding agents all day, and we needed one thing done perfectly: every word lands where we were typing. FluidVoice was growing in many directions at once: an AI assistant of its own, analytics, its own updater, connections back to its servers. we wanted the engine without the rest. so we cut MouthKeys down to the job and spent the time on what matters to us: delivery that never drops a word, a faster stop, and an interface that stays quiet until you reach for it. if you want FluidVoice's AI features, FluidVoice is the app for that.

much of *what you get* is ours; some is upstream's later work, ported by hand. [UPSTREAM.md](UPSTREAM.md) credits each commit.

### what's left out.

MouthKeys is narrower on purpose.

- **Fluid Intelligence.** FluidVoice's AI layer and its settings are not included. [#3]
- **support for AI cleanup.** the provider-based cleanup FluidVoice shipped is still in the app, under Advanced in the sidebar. we don't use it, test it or support it, and setup never asks about it. if you want it, it's yours: point your coding agent at the code and fix or change it to your heart's content.
- **telemetry.** analytics are hard-wired off and the keys are blank. [`0e2948a`][0e2948a], [#3]
- **the built-in updater.** it updates to FluidVoice, which would replace this build, so it is off. you update by downloading the new release or rebuilding. [`19202c1`][19202c1], [#3]

### upstream.

we follow FluidVoice's work and port the fixes that fit here by hand, crediting each in the commit. what we took, what we skipped, and why: [UPSTREAM.md](UPSTREAM.md).

## contributing.

bugs and ideas go in [issues](https://github.com/BenevolentFutures/MouthKeys/issues). pull requests target `main`; start with [CONTRIBUTING.md](CONTRIBUTING.md), and [docs/BUILDING.md](docs/BUILDING.md) for the build.

---

*your voice is the fastest way you have to get a thought out of your head. it should land where you meant it.*

---

## license.

GPL-3.0, unchanged from FluidVoice. See [LICENSE](LICENSE). FluidVoice versions published before 2026-02-23 were licensed under Apache License 2.0 ([upstream's note][relicense]); MouthKeys was forked after that date.

**Modification notice.** MouthKeys is a modified version of [FluidVoice](https://github.com/altic-dev/FluidVoice) by altic-dev. Atin Woodard has modified it since 2026-08-15. The changes are summarized under *what you get* and *built on FluidVoice* above; [UPSTREAM.md](UPSTREAM.md) and the git history record each one.

FluidVoice by altic-dev and its contributors built nearly all of this: the speech pipeline, hotkeys, typing, settings and model downloads. The models themselves come from NVIDIA, Cohere, OpenAI and Apple. If MouthKeys is useful to you, please [sponsor altic-dev](https://github.com/sponsors/altic-dev).

MouthKeys is not affiliated with or endorsed by altic-dev.

[base]: https://github.com/altic-dev/FluidVoice/commit/d62adc9ac35467f9933fda689111514545466a2d
[relicense]: https://github.com/altic-dev/FluidVoice/commit/76bc885e875e368fe5938fa44bd7246669c6b84f
[0e2948a]: https://github.com/BenevolentFutures/MouthKeys/commit/0e2948ac
[19202c1]: https://github.com/BenevolentFutures/MouthKeys/commit/19202c1a
[8ed75b9]: https://github.com/BenevolentFutures/MouthKeys/commit/8ed75b9a
[8ab26a8]: https://github.com/BenevolentFutures/MouthKeys/commit/8ab26a8f
[8295536]: https://github.com/BenevolentFutures/MouthKeys/commit/82955361
[68afebc]: https://github.com/BenevolentFutures/MouthKeys/commit/68afebce
[#2]: https://github.com/BenevolentFutures/MouthKeys/pull/2
[#3]: https://github.com/BenevolentFutures/MouthKeys/pull/3
[#4]: https://github.com/BenevolentFutures/MouthKeys/pull/4
[#7]: https://github.com/BenevolentFutures/MouthKeys/pull/7
[#8]: https://github.com/BenevolentFutures/MouthKeys/pull/8
[#9]: https://github.com/BenevolentFutures/MouthKeys/pull/9
[#10]: https://github.com/BenevolentFutures/MouthKeys/pull/10
[#17]: https://github.com/BenevolentFutures/MouthKeys/pull/17
[#22]: https://github.com/BenevolentFutures/MouthKeys/pull/22
[#24]: https://github.com/BenevolentFutures/MouthKeys/pull/24
[#25]: https://github.com/BenevolentFutures/MouthKeys/pull/25
[#27]: https://github.com/BenevolentFutures/MouthKeys/pull/27
[#29]: https://github.com/BenevolentFutures/MouthKeys/pull/29
[#30]: https://github.com/BenevolentFutures/MouthKeys/pull/30
