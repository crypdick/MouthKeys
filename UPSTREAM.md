# Upstream and attribution

This Linux implementation is maintained in [crypdick/MouthKeys-Linux](https://github.com/crypdick/MouthKeys-Linux).
It derives from [BenevolentFutures/MouthKeys](https://github.com/BenevolentFutures/MouthKeys),
the macOS dictation application by Benevolent Futures, originally forked from
[altic-dev/FluidVoice](https://github.com/altic-dev/FluidVoice) by altic-dev.

MouthKeys' visual language, grin artwork, and interaction design informed the Linux Qt interface.
The upstream macOS sources, artwork-generation scripts, design prototypes, and historical port
ledger remain available in this repository's Git history and in the upstream repository.
Removing macOS build products and sources does not change the GPL-3.0 license or attribution.

## Porting policy

- Keep `origin` pointing to the Linux fork and `mouthkeys-upstream` to BenevolentFutures/MouthKeys.
- Review upstream changes and adapt relevant behavior by hand. Do not merge the macOS tree back in.
- Credit a port with its upstream repository, commit SHA, subject, and original author in the commit.
- Keep Linux dictation local. Do not port telemetry, cloud AI features, or upstream auto-updaters.
- Open Linux PRs against `crypdick/MouthKeys-Linux --base main`, never the parent repository or its site.
