# MouthKeys

## Personal Linux fork

This checkout is `crypdick/MouthKeys`, Ricardo Decal's personal fork. Linux work lives in
`linux/`; read `linux/README.md` for architecture, delivery limits, and validation. The original
macOS app remains supported and its safety rules below still apply. Linux builds use
`uv sync --project linux --python 3.13 --extra gui --locked`, `uv run --project linux pytest`,
`uv run --project linux ruff check linux`, and `uv build linux`.

For this fork, PRs **must** target `crypdick/MouthKeys --base main`, overriding the upstream
repository routing below. `origin` is the personal fork; `mouthkeys-upstream` is
`BenevolentFutures/MouthKeys`. Never publish personal changes to the parent project or its site.
Keep Linux tests headless, with fake capture/clipboard/key adapters and isolated XDG directories.

macOS dictation app, forked from FluidVoice (see `UPSTREAM.md`). The product is **wicked fast voice to text**. Fluid Intelligence is removed, telemetry is hard-off (`AnalyticsConfig.isConfigured` is false), and the upstream updater is off (`AppDelegate.upstreamUpdatesDisabled`). Keep all three that way. An updater of our own, Sparkle 2, is decided and planned in `docs/UPDATES.md`; until that build lands, the app checks for nothing.

Atin dictates into Claude Code in c11 all day with the installed app. Text delivery into c11 and Ghostty (forced Reliable Paste) must never regress.

## Private software, pushed to done

MouthKeys is open source (public repo, mouthkeys.com, a DMG per release), but in practice it is still private software: Atin is its user. The public surface does not make it a released product with live users, so set the autonomy dial to pre-release. Make the calls yourself and push every change all the way through: branch, build, test, a fresh-context review, PR, merge, without stopping to ask. Ask only for what Atin alone can do or decide (a permission prompt, a feel or sound check, a real product fork).

Three things still wait for Atin, and they are about his machine, not the public: installing (below), anything that touches the installed app (below), and `scripts/release.sh publish` (after he has dictated with the new build).

## Identity

| | Installed (Release) | Debug build and test host |
|---|---|---|
| Bundle ID | `com.stage11.mouthkeys` | `com.stage11.mouthkeys.dev` |
| Application Support | `~/Library/Application Support/MouthKeys` | `.../MouthKeys-Dev` |
| Log | `~/Library/Logs/MouthKeys/Fluid.log` | `~/Library/Logs/MouthKeys-Dev/Fluid.log` |

- Earlier identities (`PreviousAppIdentity.newestFirst`): MouthKeys 0.1.0 ran under the app's earlier working identifiers (bundle ID, Application Support folder and settings-key prefix listed in `AppStorageLocation.swift`, the only place they may appear), and before that the app ran as FluidVoice (`com.FluidApp.app`, `Application Support/FluidVoice`). On its first launch the installed app copies the newest earlier identity that has data once (`AppIdentityMigration`, run from `MouthKeysMain` before anything reads a default): every UserDefaults key except that identity's own bookkeeping (its migration markers and Accessibility trust record), then the folder, then the login item. It never writes to the old domain or folder, so the old app still runs from a backup. Check it with `grep IDENTITY_MIGRATION ~/Library/Logs/MouthKeys/Fluid.log`; the markers are `MouthKeysIdentityMigrationDefaults` and `MouthKeysIdentityMigrationFolder` in the new domain. The old data wins on conflict; what it replaces is saved to `~/Backups/mouthkeys-displaced-*` first. A retry that had to set data aside and still failed stops retrying (`MouthKeysIdentityMigrationDefaultsHalted`) and shows an alert before the app opens. Debug builds never migrate. A new bundle ID is a new app to macOS: Microphone and Accessibility are granted once more after the migration.
- Identifiers live in `AppStorageLocation` (and `PreviousAppIdentity` for the old ones). Never hardcode one. The keychain service `com.fluidvoice.provider-api-keys` kept its name on purpose (`KeychainService.serviceName`).
- Model caches in `~/Library/Application Support/FluidAudio` belong to the FluidAudio library, not to a bundle ID, and are shared by every build.
- Install with Atin only, and pick the path by the installed app's signer (`codesign -dvv /Applications/MouthKeys.app 2>&1 | grep -m1 Authority=`). **Developer ID** (Atin's Mac since the 0.1.0 DMG): never `./build.sh install`. A release is `scripts/release.sh ship --notes FILE` (build on Atlas, sign, notarize, draft, install here, then `publish` once Atin has dictated); a packaged app alone goes in with `scripts/release.sh install <app>`, which is "Install over a Developer ID app" in `docs/INSTALL-CHECKLIST.md` as a script (pitfall below). **Apple Development**: `./build.sh install` checks for data already under a new identity (first install only), quits the app (and stops if it will not quit), backs it up to `~/Backups/mouthkeys-<timestamp>/` and verifies the copy, prints the rollback command (`bash ~/Backups/mouthkeys-<timestamp>/rollback.sh`), then copies the new app alongside and swaps it in. Then run `docs/INSTALL-CHECKLIST.md`.
- Never launch a Release product (`./build.sh release`, `DerivedData/.../Release/MouthKeys.app`): it is `com.stage11.mouthkeys`, the installed app's identity, and would write into the installed app's defaults and folder. The migration only runs for the app in `/Applications`.

## Never touch the installed app

- Never touch `/Applications/MouthKeys.app`, quit or relaunch the running app, write `defaults` for `com.stage11.mouthkeys` or any earlier identity's domain, or touch `~/Library/Application Support/MouthKeys` or an earlier identity's folder. Never run `./build.sh install` without Atin.
- Debug builds are isolated by their own bundle ID (own UserDefaults) and folders (table above). Any code that picks an Application Support folder must use `AppStorageLocation.folderName`, and the log folder `AppStorageLocation.logFolderName`.
- Read either log freely.

## Build

```sh
xcodebuild -project Fluid.xcodeproj -scheme Fluid -configuration Debug -destination 'platform=macOS' \
  -derivedDataPath DerivedData DEVELOPMENT_TEAM="$MOUTHKEYS_DEVELOPMENT_TEAM" SDK_STAT_CACHE_ENABLE=NO build
```

- `MOUTHKEYS_DEVELOPMENT_TEAM` is your own 10-character Apple team ID (the maintainer uses his own; contributors pass theirs). `./build.sh` reads the same variable.
- Always pass `SDK_STAT_CACHE_ENABLE=NO`. On this machine `clang-stat-cache` hangs at 0% CPU on its second run in a DerivedData folder, and the build sits at "ClangStatCache" with no error. If you see that, kill `clang-stat-cache` and re-run with the flag.
- Product: `DerivedData/Build/Products/Debug/MouthKeys Debug.app`. The test module is `MouthKeys_Debug` (`@testable import MouthKeys_Debug`).
- The warning about `CTranscribe.framework/Versions/Current` symlinks is harmless for Debug builds.

## Test

- Same command with `test`. Iterate with `-only-testing:FluidDictationIntegrationTests/<Suite>`, then run the full suite before a PR.
- The test host is `MouthKeys Debug.app`, which launches briefly. Never click through or dismiss a system permission prompt; report it.
- **App-hosted tests must stay invisible and silent on the operator's machine.** Atin works (and dictates with the installed app) while tests run. As the XCTest host the app runs in `TestHostQuietMode`: it never activates, puts no window on screen, has no menu bar item, installs no global monitor or event tap, posts no notification, asks for no permission, and creates no sound player. `TestHostQuietModeTests` guards this. Never add a test or benchmark that shows UI, plays audio, takes focus, types, or touches the clipboard, and batch repeated runs inside one test-host launch.
- Never wait on a real `NSAnimationContext` completion in a test. Window animations evidently tick on the display (a run ended the moment the displays woke), so while the displays sleep the completion never comes and the suite hangs (`DatasheetFloatShadowTests`, 2026-10-01). Step the animated value by hand, and in an async test spell out `completionHandler: nil`: the bare `runAnimationGroup { }` there is the async overload, which awaits completion. Every wait gets a timeout of a few seconds (`fulfillment(of:timeout:)`, or a polled deadline).
- `DirectAudioReliabilityTests.testReadinessGateRearmingCancelsExistingWaiter` was flaky (a test race) until `4474074e`. If it fails again, re-run it alone before calling it a regression.
- App sources are a synchronized folder; test files are listed in `project.pbxproj` by hand. A new test file needs a project entry, so prefer adding to an existing test file.
- swiftlint and swiftformat are not installed. Follow `.swiftlint.yml`, `.swiftformat` and the surrounding code.

## Validate

Green tests are not a working product. Mic capture, Accessibility and real paste into c11 need a check in the running app. When you cannot drive it yourself, hand Atin concrete steps. After every install, Atin runs `docs/INSTALL-CHECKLIST.md`; add a line there when a change needs a real-path check.

Scripted delivery checks (Debug builds only): `defaults write com.stage11.mouthkeys.dev MouthKeysDebugDeliveryTriggers -bool YES`, then post a `com.stage11.mouthkeys.debug.*` distributed notification (see `DeliveryDebugTriggers.swift`). `toggleDictation` and `cancelDictation` drive a dictation without the hotkey; `logOverlayTargets` logs the overlay's mic label and the microphone card in global top-left coordinates, for a real click with `cliclick`. Launched straight from a c11 shell, a Debug build inherits c11's Microphone and Accessibility grants; first move its shortcuts off Atin's keys (its own `.dev` defaults: `PrimaryDictationShortcuts`, `CancelRecordingHotkeyShortcut`) so its event tap never answers his hotkey.

## Website

mouthkeys.com is `site/` (one static page in light Datasheet Mono, the app's visual language, called Signal in code; the grin in `site/grin.js` is ported from `scripts/make_app_icon.swift`). `.github/workflows/pages.yml` deploys it to GitHub Pages on every push to `main` that touches `site/` or `docs/images/`. Preview: `site/assemble.sh <dir>` then serve `<dir>` on localhost. The page reads the latest release from the GitHub API for the version and the DMG link, so a new release needs no site change. DNS lives in the Stage11 Projects Cloudflare account (apex A/AAAA and `www` CNAME to GitHub Pages, DNS only); see `~/Projects/Stage11/code/platform/cloudflare.md`.

## Git and PRs

- `gh repo set-default` is `BenevolentFutures/MouthKeys` (GitHub redirects the repo's earlier URL). The integration branch is `main`.
- Always `gh pr create --repo BenevolentFutures/MouthKeys --base main`. Never open anything against `altic-dev/FluidVoice`.
- Upstream fixes are ported by hand, never merged. Policy, watermark and ledger: `UPSTREAM.md`.

## Agent pitfalls

### `./build.sh install` over the Developer ID app silently kills the hotkeys

**The incident (2026-10-02):** with the Developer ID 0.1.0 build installed, an agent ran `./build.sh install`. It signs with the Apple Development identity: same bundle ID, a different designated requirement. Accessibility still showed switched on, `AXIsProcessTrusted()` was false, and the hotkey retried `Attempt 1 failed` until the install was rolled back.

**The rule:** match the installed app's signer (for a same-ID update; the one install that changes the bundle ID compares the signer only and expects `waiting_for_accessibility` until Accessibility is granted, see the checklist's step 3). Over a Developer ID app, sign the Release build with Developer ID (`scripts/release.sh package`, notarizing optional for a local install), confirm `codesign -d -r-` matches the installed app's line exactly, then swap it in by hand: "Install over a Developer ID app" in `docs/INSTALL-CHECKLIST.md`. After the swap, `grep HOTKEY_TAP ~/Library/Logs/MouthKeys/Fluid.log | tail -1` must say `state=installed`; `waiting_for_accessibility` means the signature does not match, so roll back.

### A new signature leaves a stale Accessibility grant, and other copies of the bundle ID poison it

**The incident (2026-10-02):** Atin replaced an Apple Development-signed build with the Developer ID-signed 0.1.0 DMG (same bundle ID, new signature). MouthKeys showed as switched on in Privacy & Security > Accessibility, yet `AXIsProcessTrusted()` stayed false: onboarding kept saying Open Settings and the hotkeys were silently dead (the old retry logged `Attempt 1 failed` every 0.5 s, forever). Removing the row with − and switching it on again did not help. tccd logged `Failed to match existing code requirement for subject <the app's bundle ID> and service kTCCServiceAccessibility`: other copies with the same bundle ID and a different signer were registered with LaunchServices (an old copy in the Trash, a `~/Library/Caches/com.apple.SwiftUI.Drag-*/` copy, an old DerivedData Release build), and System Settings recorded one of their code requirements when the switch was flipped.

**What the app does now:** `AccessibilityTrustMonitor` re-reads trust every 0.5 s while a permission surface is visible and on every activation; the hotkey tap arms itself the moment trust flips (`HOTKEY_TAP state=waiting_for_accessibility`, then `state=installed`, transitions logged once). Still untrusted 3 s after the user returns from System Settings, the step shows "Already switched on?", and `ConflictingAppCopyDetector` names any registered copy whose designated requirement the running app does not satisfy (`PERMISSION_DIAG conflicting_copies=N paths=...`) with Show in Finder. Trusted but the tap refused after five tries: `state=failed_trusted` and a Relaunch MouthKeys button. It never deletes anything.

**The rules:**
1. Before the first launch of a build with a new signature, delete other copies of `com.stage11.mouthkeys` signed by someone else and empty the Trash. `./build.sh install` lists them after installing (read-only).
2. Diagnose from the log first: `grep -E 'HOTKEY_TAP|ACCESSIBILITY|PERMISSION_DIAG|PERMISSION_HINT' ~/Library/Logs/MouthKeys/Fluid.log`, and tccd's view with `log show --last 10m --predicate 'process == "tccd"' | grep mouthkeys`.
3. Agents never touch TCC (`tccutil`) or delete Atin's copies. Hand him the paths and the steps.
