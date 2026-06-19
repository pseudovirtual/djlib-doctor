# djlib-doctor

Read-only-first, cue-safe DJ library verification, cleanup planning, and dry-run/staged porting for Rekordbox and Serato.

`djlib-doctor` helps DJs and coding agents inspect messy libraries, plan cleanup, compare exports, and stage migrations without silently rewriting creative metadata. It treats hotcues, memory cues, loops, playlist order, and source files as things to verify before touching.

This is an open-source project from [@pseudovirtual](https://github.com/pseudovirtual) for DJs who want safer, inspectable alternatives to opaque library cleanup and migration tools.

## What It Does

- verifies Rekordbox XML exports
- detects local Rekordbox and Serato library paths read-only
- separates collection tracks from playlist references
- treats streaming placeholders as placeholders, not missing files
- parses memory cues, hotcues, cue loops, and loop end times
- creates snapshots and redacted shareable reports
- plans missing-file, duplicate, cue, bad-path, and audio-format cleanup
- fingerprints local files for exact-duplicate and raw-byte similarity checks
- compares two arbitrary files as `exact_duplicate`, `byte_similar`, or `different`
- supports duplicate policies: `cue-safe`, `quality`, and `keep-both`
- records interactive review decisions
- compares baseline/final exports for lost material or cue regressions
- dry-runs Rekordbox-to-Serato and Serato-to-Rekordbox migrations
- certifies migration previews and staged artifacts with machine-readable scorecards
- scopes migration plans to one track, one playlist/crate, many playlists, or a whole collection
- supports transfer modes: `full`, `cues-only`, and `match-only`
- stages implemented write workflows behind explicit approvals and install tokens

## Experimental / Limited Coverage

- Serato audio tag writes and Serato Markers2 cue import are fixture-tested and need broader real-world validation.
- Rekordbox encrypted `master.db` reads and staged writes are generated-fixture tested through pyrekordbox; real captured DB certification is still pending.
- Acoustic fingerprinting is planned behind an optional backend; current fingerprinting is byte-level only.

## Safety Model

Planning commands do not write to live libraries. Write-capable flows are split into explicit `stage ...` and `install ...` commands that verify:

exact confirmation tokens, recomputed manifest tokens, staged hashes, live source hashes from staging time, backups, and app/SQLite sidecar checks where relevant.

## Why Cue-Safe Migration Is Hard

DJ apps store creative timing in several places: library databases, audio tags, ANLZ files, crates, XML exports, and sometimes player-specific analysis caches. A cue-safe workflow has to preserve cue kind, hotcue slot, loop end, playlist order, file path, and encoder-delay behavior together, so `djlib-doctor` previews and stages changes before installing them.

## Quick Start

```bash
git clone https://github.com/pseudovirtual/djlib-doctor.git
cd djlib-doctor
python3 -m pip install -e .
djlib-doctor verify tests/fixtures/rekordbox/simple.xml --no-file-check
djlib-doctor detect
djlib-doctor examples
djlib-doctor self-test
```

Serato audio tag staging needs optional dependencies: `python3 -m pip install -e ".[audio-tags]"`.

Rekordbox `master.db` work uses default dependencies: `pyrekordbox` and `sqlcipher3-wheels`. If SQLCipher cannot import on your platform, Rekordbox DB commands fail closed with a backend-unavailable message.

SQLCipher support depends on prebuilt `sqlcipher3-wheels` coverage. The supported binary-wheel matrix currently covers the project CI targets: Ubuntu x64, Windows x64, and current GitHub macOS arm64 runners on Python 3.9 and 3.13. Prebuilt wheels are not available for every platform/Python combination; the known gap is Intel/x86_64 macOS on Python 3.13, where `pip install` may fail to build SQLCipher locally. On Intel macOS, use Python <=3.12 for now; Apple Silicon users should prefer the normal supported Python versions.

Run the full suite:

```bash
python3 -m pip install -e ".[dev]"
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src PYTHONPYCACHEPREFIX=work/pycache python3 -m compileall -q src tests
```

## Human Workflows

These examples use `run/` as a scratch folder. Planning commands are read-only. Commands that can touch live libraries are split into `stage ...` and `install ...` with explicit confirmation tokens.

### 1. Check A Rekordbox XML Export

Export your collection from Rekordbox, then verify the XML. If config or detection finds it, the path can be omitted:

```bash
djlib-doctor detect
djlib-doctor verify ~/Desktop/rekordbox-export.xml
djlib-doctor verify
```

For a shareable diagnostic bundle, add a redacted snapshot:

```bash
djlib-doctor snapshot --rekordbox-xml ~/Desktop/rekordbox-export.xml --music-root ~/Music --out run/check-redacted --redact-paths
```

### 2. Find Missing Files Without Treating Streaming Tracks As Broken

```bash
djlib-doctor snapshot --rekordbox-xml ~/Desktop/rekordbox-export.xml --music-root ~/Music --out run/missing
djlib-doctor plan missing-files --snapshot run/missing/snapshot.json --out run/missing/plan.json
djlib-doctor review --plan run/missing/plan.json --out run/missing/review.json
djlib-doctor apply-manifest --plan run/missing/plan.json --review-log run/missing/review.json --only-reviewed --out run/missing/apply.json
```

The interactive review saves JSON decisions. Reviewed path updates can be staged into a copied Rekordbox DB and installed only with the printed token:

```bash
djlib-doctor stage rekordbox-db-apply --db /path/to/rekordbox/master.db --apply-manifest run/missing/apply.json --stage-dir run/rekordbox-apply
djlib-doctor install rekordbox-db --stage-dir run/rekordbox-apply --db /path/to/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
```

### 3. Review Duplicates With A Collision Policy

```bash
djlib-doctor snapshot --rekordbox-xml ~/Desktop/rekordbox-export.xml --music-root ~/Music --out run/dupes
djlib-doctor plan duplicates --snapshot run/dupes/snapshot.json --out run/dupes/plan.json --collision-policy cue-safe
djlib-doctor review --plan run/dupes/plan.json --out run/dupes/review.json
```

Other duplicate policies: `quality` and `keep-both`.

### 4. Compare Before And After Exports

```bash
djlib-doctor compare exports --baseline ~/Desktop/rekordbox-before.xml --final ~/Desktop/rekordbox-after.xml --out run/compare.json
```

### 5. Compare Two Files By Bytes

```bash
djlib-doctor fingerprint compare ~/Music/copy-a.wav ~/Music/copy-b.wav --out run/file-compare.json
```

### 6. Convert A Rekordbox Track Without Losing Cues

Prepare a small operations file naming the track, source, converted target, preset, and Rekordbox ANLZ files. See [Convert Without Losing Cues](docs/how-to-convert-without-losing-cues.md) for the full staged workflow.

```bash
djlib-doctor stage rekordbox-convert --db /path/to/rekordbox/master.db --operations run/convert.json --stage-dir run/rekordbox-convert --cue-shift auto
djlib-doctor install rekordbox-convert --stage-dir run/rekordbox-convert --db /path/to/rekordbox/master.db --confirm-token INSTALL_REKORDBOX_CONVERT:...
```

### 7. Move Or Rename A Rekordbox Track Safely

Use `rekordbox-move` when the file location should change and Rekordbox should point at the new path in the same staged install.

```bash
djlib-doctor stage rekordbox-move --db /path/to/rekordbox/master.db --operations run/move.json --stage-dir run/rekordbox-move
djlib-doctor install rekordbox-move --stage-dir run/rekordbox-move --db /path/to/rekordbox/master.db --confirm-token INSTALL_REKORDBOX_MOVE:...
```

### 8. Dry-Run A Rekordbox To Serato Playlist Port

```bash
djlib-doctor port rb-to-serato --rekordbox-xml ~/Desktop/rekordbox-export.xml --playlist "ROOT / My Set" --out run/rb-to-serato --verify-preview
djlib-doctor certify rb-to-serato --port-manifest run/rb-to-serato/port-manifest.json --out run/rb-to-serato/certification.json
```

Inspect the manifest, crate preview, and `unsupported.csv`. If it looks right, stage and install only with the printed token:

```bash
djlib-doctor stage serato --port-manifest run/rb-to-serato/port-manifest.json --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --stage-dir run/serato-stage
djlib-doctor install serato-stage --stage-dir run/serato-stage --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --confirm-token INSTALL_SERATO_STAGE:...
```

### 9. Choose Scope And Transfer Mode

```bash
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --track-id 123 --transfer-mode cues-only --out run/one-track-cues
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --collection --transfer-mode match-only --out run/collection-match
djlib-doctor port serato-to-rb --serato-library-dir /path/to/serato-library --portable-id "Music/Track.aiff" --collection-root ~/Music --transfer-mode cues-only --out run/serato-track-cues
djlib-doctor port serato-to-rb --serato-library-dir /path/to/serato-library --collection --collection-root ~/Music --out run/serato-collection
```

Transfer modes: `full`, `cues-only`, and `match-only`.

### 10. Port A Serato Crate Toward Rekordbox

Full walkthrough: [Port One Serato Crate To Rekordbox](docs/how-to-port-one-crate.md).

```bash
djlib-doctor port serato-to-rb --serato-library-dir /path/to/serato-library --crate /path/to/_Serato_/Subcrates/MySet.crate --collection-root ~/Music --out run/serato-to-rb
djlib-doctor certify serato-to-rb --port-manifest run/serato-to-rb/port-manifest.json --out run/serato-to-rb/certification.json
```

This writes a dry-run manifest and `rekordbox-preview.xml` for inspection. The intended write path is staged `master.db` install, not manual XML import as the final step:

```bash
djlib-doctor stage rekordbox-db-import --db /path/to/rekordbox/master.db --port-manifest run/serato-to-rb/port-manifest.json --stage-dir run/rekordbox-stage
djlib-doctor install rekordbox-db --stage-dir run/rekordbox-stage --db /path/to/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
djlib-doctor migrate serato-to-rb --serato-library-dir /path/to/serato-library --crate /path/to/_Serato_/Subcrates/MySet.crate --collection-root ~/Music --out run/serato-to-rb --stage-db --rekordbox-db /path/to/rekordbox/master.db
```

### 11. Let An Agent Help, Safely

In Codex, Claude Desktop, or another local coding agent, ask for read-only help first:

```text
Use djlib-doctor to inspect my Rekordbox XML export. Stay read-only, explain the findings in DJ language, and do not modify my library.
```

## Project Status

Implemented: verification, snapshots, cleanup plans, review logs, schema output, export comparison, byte fingerprinting, migration certification, Serato inspection, two-way dry-run porting, and staged/token-gated install workflows. Still pre-release: polished release automation, broader real-world Serato cue/tag validation, and certified Rekordbox DB version coverage.
More docs: [index](docs/README.md), [features](docs/feature-list.md), [workflows](docs/human-workflows.md), [convert](docs/how-to-convert-without-losing-cues.md), [crate port](docs/how-to-port-one-crate.md), [Serato porting](docs/serato-porting.md), [architecture](docs/product-architecture.md).
