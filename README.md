# djlib-doctor

[![PyPI version](https://img.shields.io/pypi/v/djlib-doctor.svg)](https://pypi.org/project/djlib-doctor/)
[![Python versions](https://img.shields.io/pypi/pyversions/djlib-doctor.svg)](https://pypi.org/project/djlib-doctor/)
[![Tests](https://github.com/pseudovirtual/djlib-doctor/actions/workflows/tests.yml/badge.svg)](https://github.com/pseudovirtual/djlib-doctor/actions/workflows/tests.yml)
[![License](https://img.shields.io/pypi/l/djlib-doctor.svg)](https://github.com/pseudovirtual/djlib-doctor/blob/main/LICENSE)

A safety-first command-line tool for cleaning up your DJ library and moving it between **Rekordbox** and **Serato** — designed to preserve supported hot cue, loop, and playlist metadata.

Most library cleanup and migration tools rewrite your work and hope for the best. `djlib-doctor` does the opposite: it **looks first, shows you what it found, and only changes anything after you confirm.** Your cues, memory points, loops, and playlist order are treated as work worth protecting, not data to be silently overwritten.

Open-source, from [@pseudovirtual](https://github.com/pseudovirtual).

## What you can do with it

- **Check your library for problems** — missing files, duplicates, broken paths — before they bite you mid-set.
- **Move a track, a playlist, or your whole collection** between Rekordbox and Serato, preserving supported cue and loop metadata.
- **Convert WAVs to M4A** (or other formats) without your cues drifting out of place.
- **Move or rename tracks** and have Rekordbox follow the file instead of going "track not found."
- **Find real duplicates** and decide what to keep with cue-aware rules.
- **Get a clean report** you can share for help without exposing your folder paths.

It never streams your library anywhere or touches your files until you say so.

## Quick start

```bash
python3 -m pip install djlib-doctor
djlib-doctor detect        # find your Rekordbox / Serato libraries
djlib-doctor examples      # see common commands for your setup
djlib-doctor self-test     # confirm everything installed correctly
```

That's enough to start poking at your library read-only. The first thing most people run:

```bash
djlib-doctor verify ~/Desktop/rekordbox-export.xml
```

> Working with Serato audio tags? Add the optional extras: `pip install "djlib-doctor[audio-tags]"`.

## How it keeps your library safe

Anything that *reads* your library runs freely and changes nothing.

Anything that *writes* is split into two deliberate steps — `stage` (prepare and preview the change) and `install` (apply it) — and the install only goes through if you paste back an exact confirmation token it printed. Before touching a live file it verifies hashes, backups, sidecars, and app-closed state where relevant. If anything looks off, it stops rather than guessing.

In plain terms: **it can't quietly rewrite your collection. You always see the change and approve it first.**

## Common tasks

A few of the most common workflows are below. Full step-by-step guides live in [docs/human-workflows.md](docs/human-workflows.md).

**Check a Rekordbox export for missing files (without flagging streaming tracks as broken):**

```bash
djlib-doctor snapshot --rekordbox-xml ~/Desktop/rekordbox-export.xml --music-root ~/Music --out run/missing
djlib-doctor plan missing-files --snapshot run/missing/snapshot.json --out run/missing/plan.json
djlib-doctor review --plan run/missing/plan.json --out run/missing/review.json
```

**Convert a track without losing cues:**

```bash
djlib-doctor stage rekordbox-convert --db /path/to/rekordbox/master.db --operations run/convert.json --stage-dir run/rekordbox-convert --cue-shift auto
djlib-doctor install rekordbox-convert --stage-dir run/rekordbox-convert --db /path/to/rekordbox/master.db --confirm-token INSTALL_REKORDBOX_CONVERT:...
```

**Dry-run a Rekordbox → Serato playlist port:**

```bash
djlib-doctor port rb-to-serato --rekordbox-xml ~/Desktop/rekordbox-export.xml --playlist "ROOT / My Set" --out run/rb-to-serato --verify-preview
```

You can scope any port to one track, one playlist/crate, or your whole collection, and choose how much to carry over (`full`, `cues-only`, or `match-only`). See the [workflows guide](docs/human-workflows.md) for porting in both directions, moving/renaming tracks, and the staged install steps.

**Let a coding agent help, safely:**

```text
Use djlib-doctor to inspect my Rekordbox XML export. Stay read-only,
explain the findings in DJ language, and don't modify my library.
```

## Under the hood

The detail below is for the curious and for contributors — you don't need any of it to use the tool.

<details>
<summary><strong>What's been validated against real libraries</strong></summary>

- **Rekordbox encrypted `master.db`** reads through pyrekordbox/SQLCipher: tracks, playlists, and hot cues, memory cues, and saved loops via the real `InMsec`/`OutMsec`/`Kind`/`is_hot_cue`/`is_memory_cue` schema.
- **Cue-safe conversion** shifts cues by the net encoder delay so WAV/AIFF/MP3 → M4A keeps cues aligned. Validated on a real Rekordbox 7.2.8 library including an encrypted write round-trip where the cue persisted. (Rekordbox 7+ didn't compensate AAC gapless metadata in that test, so the positive cue shift is required.)
- **Serato Markers2 cue writes** use Serato's real container shape (version header + base64 body); a written hot cue showed up at the exact position in real Serato DJ.
- **Serato reads** cover real crates, real `database V2` records (`pfil`/`tsng`/`tart`/`talb`/`tgen`/`tkey`), and Serato Markers2/BeatGrid tags.
- **Rekordbox ANLZ** beatgrid (`PQTZ`/`PQT2`) and cue container (`PCOB`/`PCO2`) offsets parse correctly on real analysis files.

</details>

<details>
<summary><strong>Known limits & experimental areas</strong></summary>

- ANLZ beat-shift during conversion is lightly covered end-to-end; parsing is validated, but the write path still needs a real track-with-ANLZ round-trip.
- Serato saved-loop display isn't yet verified in the Serato GUI (hot cue display is).
- Version coverage beyond Rekordbox 7.2.8 and captured Serato DJ Pro data is still experimental.
- Fingerprinting is byte-level only today; acoustic fingerprinting is planned behind an optional backend.

</details>

<details>
<summary><strong>Platform / SQLCipher notes</strong></summary>

Rekordbox `master.db` work uses `pyrekordbox` and `sqlcipher3-wheels` (installed by default). Prebuilt SQLCipher wheels cover the CI targets — Ubuntu x64, Windows x64, and current GitHub macOS arm64 runners on Python 3.9 and 3.13. The known gap is **Intel/x86_64 macOS on Python 3.13**, where `pip install` may fail to build SQLCipher locally; use Python ≤3.12 there for now. If SQLCipher can't import, Rekordbox DB commands fail closed with a clear backend-unavailable message rather than doing anything risky.

</details>

<details>
<summary><strong>Why cue-safe migration is genuinely hard</strong></summary>

DJ apps scatter creative timing across several places: library databases, audio tags, ANLZ files, crates, XML exports, and player-specific analysis caches. A cue-safe workflow has to preserve cue kind, hotcue slot, loop end, playlist order, file path, and encoder-delay behavior *together* — which is why `djlib-doctor` previews and stages changes before installing them.

</details>

## For developers

```bash
git clone https://github.com/pseudovirtual/djlib-doctor.git
cd djlib-doctor
python3 -m pip install -e ".[dev]"
PYTHONPATH=src python3 -m unittest discover -s tests
```

More docs: [index](docs/README.md) · [features](docs/feature-list.md) · [workflows](docs/human-workflows.md) · [convert](docs/how-to-convert-without-losing-cues.md) · [crate port](docs/how-to-port-one-crate.md) · [Serato porting](docs/serato-porting.md) · [architecture](docs/product-architecture.md).

## Project status

Released as `0.1.0` on PyPI. Implemented: verification, snapshots, cleanup plans, review logs, export comparison, byte fingerprinting, migration certification, Serato inspection, two-way dry-run porting, and staged/token-gated installs — green on Ubuntu, macOS, and Windows (Python 3.9 and 3.13). Still maturing: broader version coverage, ANLZ write-path round-trip validation, and Serato saved-loop GUI verification.
