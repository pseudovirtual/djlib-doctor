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
- stages implemented write workflows behind explicit install tokens

## Experimental / Limited Coverage

- Serato audio tag writes and Serato Markers2 cue import are fixture-tested and need broader real-world validation.
- No real Rekordbox DB version is certified yet; only tested plain-SQLite `master.db` schemas are supported.
- Acoustic fingerprinting is planned behind an optional backend; current fingerprinting is byte-level only.

## Safety Model

Planning commands do not write to live libraries. Write-capable flows are split into explicit `stage ...` and `install ...` commands that verify:

- exact confirmation token
- token recomputed from manifest contents
- staged file hashes
- live source hashes from staging time
- backups
- app/SQLite sidecar checks where relevant

## Quick Start

```bash
git clone https://github.com/pseudovirtual/djlib-doctor.git
cd djlib-doctor
python3 -m pip install -e .
djlib-doctor verify tests/fixtures/rekordbox/simple.xml --no-file-check
djlib-doctor detect
djlib-doctor self-test
```

Serato audio tag staging needs optional dependencies: `python3 -m pip install -e ".[audio-tags]"`.

Encrypted Rekordbox DB fixture generation and future Rekordbox DB adapters need optional dependencies: `python3 -m pip install -e ".[rekordbox]"`.

Run the full suite:

```bash
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

For a shareable diagnostic bundle:

```bash
djlib-doctor snapshot --rekordbox-xml ~/Desktop/rekordbox-export.xml --music-root ~/Music --out run/check
djlib-doctor snapshot --rekordbox-xml ~/Desktop/rekordbox-export.xml --music-root ~/Music --out run/check-redacted --redact-paths
```

Use the redacted snapshot when asking for help publicly.

### 2. Find Missing Files Without Treating Streaming Tracks As Broken

```bash
djlib-doctor snapshot --rekordbox-xml ~/Desktop/rekordbox-export.xml --music-root ~/Music --out run/missing
djlib-doctor plan missing-files --snapshot run/missing/snapshot.json --out run/missing/plan.json
djlib-doctor review --plan run/missing/plan.json --out run/missing/review.json
```

The interactive review walks you through the plan one decision at a time and saves your choices as JSON for later steps.

### 3. Review Duplicates With A Collision Policy

Start with the conservative default:

```bash
djlib-doctor snapshot --rekordbox-xml ~/Desktop/rekordbox-export.xml --music-root ~/Music --out run/dupes
djlib-doctor plan duplicates --snapshot run/dupes/snapshot.json --out run/dupes/plan.json --collision-policy cue-safe
djlib-doctor review --plan run/dupes/plan.json --out run/dupes/review.json
```

Other policies are available when you know what you want: `quality` and `keep-both`.

### 4. Compare Before And After Exports

After a manual cleanup or migration attempt, export XML again and compare:

```bash
djlib-doctor compare exports --baseline ~/Desktop/rekordbox-before.xml --final ~/Desktop/rekordbox-after.xml --out run/compare.json
```

This checks for missing material, cue regressions, playlist differences, and bad final paths.

### 5. Compare Two Files By Bytes

Use byte fingerprints when you need to decide whether two local files are exact duplicates or close enough at the byte level to review manually:

```bash
djlib-doctor fingerprint compare ~/Music/copy-a.wav ~/Music/copy-b.wav --out run/file-compare.json
djlib-doctor fingerprint scan ~/Music --out run/fingerprints.json --redact-paths
```

This is not acoustic matching. A future optional `fingerprint` extra can add a real acoustic backend without changing the read-only safety boundary.

### 6. Dry-Run A Rekordbox To Serato Playlist Port

Start with a preview before staging anything:

```bash
djlib-doctor port rb-to-serato --rekordbox-xml ~/Desktop/rekordbox-export.xml --playlist "ROOT / My Set" --out run/rb-to-serato --verify-preview
djlib-doctor certify rb-to-serato --port-manifest run/rb-to-serato/port-manifest.json --out run/rb-to-serato/certification.json
```

Inspect `run/rb-to-serato/port-manifest.json`, the crate preview, and `unsupported.csv`. If it looks right, stage and install only with the printed token:

```bash
djlib-doctor stage serato --port-manifest run/rb-to-serato/port-manifest.json --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --stage-dir run/serato-stage
djlib-doctor install serato-stage --stage-dir run/serato-stage --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --confirm-token INSTALL_SERATO_STAGE:...
```

### 7. Choose Scope And Transfer Mode

Use the same port command shape for smaller or larger jobs:

```bash
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --track-id 123 --transfer-mode cues-only --out run/one-track-cues
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --collection --transfer-mode match-only --out run/collection-match
djlib-doctor port serato-to-rb --serato-library-dir /path/to/serato-library --portable-id "Music/Track.aiff" --collection-root ~/Music --transfer-mode cues-only --out run/serato-track-cues
djlib-doctor port serato-to-rb --serato-library-dir /path/to/serato-library --collection --collection-root ~/Music --out run/serato-collection
```

`full` plans tracks plus cue intent where the source adapter can read it. `cues-only` marks the manifest for cue migration onto existing matched tracks. `match-only` creates track matching/playlist structure with no cue writes.

### 8. Port A Serato Crate Toward Rekordbox

```bash
djlib-doctor port serato-to-rb --serato-library-dir /path/to/serato-library --crate /path/to/_Serato_/Subcrates/MySet.crate --collection-root ~/Music --out run/serato-to-rb
djlib-doctor certify serato-to-rb --port-manifest run/serato-to-rb/port-manifest.json --out run/serato-to-rb/certification.json
```

This writes a dry-run manifest and `rekordbox-preview.xml` representation for inspection. The intended write path is not manual XML import as the final step. Rekordbox writes should be staged against a copied `master.db`, then installed only through `install rekordbox-db` after token, hash, sidecar, and backup checks pass.

Use the explicit stage/install flow, or one-command staging:

```bash
djlib-doctor stage rekordbox-db-import --db /path/to/rekordbox/master.db --port-manifest run/serato-to-rb/port-manifest.json --stage-dir run/rekordbox-stage
djlib-doctor install rekordbox-db --stage-dir run/rekordbox-stage --db /path/to/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
djlib-doctor migrate serato-to-rb --serato-library-dir /path/to/serato-library --crate /path/to/_Serato_/Subcrates/MySet.crate --collection-root ~/Music --out run/serato-to-rb --stage-db --rekordbox-db /path/to/rekordbox/master.db
```

The DB importer currently supports only plain SQLite `master.db` files with the tested `djmdContent` columns and optional `djmdCue` cue table. Modern encrypted SQLCipher Rekordbox databases are not supported and fail closed with a specific error.

### 9. Let An Agent Help, Safely

In Codex, Claude Desktop, or another local coding agent, ask for read-only help first:

```text
Use djlib-doctor to inspect my Rekordbox XML export. Stay read-only, explain the findings in DJ language, and do not modify my library.
```

## Project Status

Implemented: verification, snapshots, cleanup plans, review logs, schema output, export comparison, byte fingerprinting, migration certification, Serato inspection, two-way dry-run porting, and staged/token-gated install workflows.

Still pre-release: polished package distribution, CI/release automation, broader real-world Serato cue/tag fixture validation, certified Rekordbox DB version coverage, and broader playlist/cue table coverage.

Serato support boundary: fixture-backed parsing covers crates, `root.sqlite` inspection, and `_Serato_/database V2` track extraction. No specific real Serato version is certified until anonymized real fixtures are added.

More docs: [index](docs/README.md), [features](docs/feature-list.md), [workflows](docs/human-workflows.md), [Serato porting](docs/serato-porting.md), [architecture](docs/product-architecture.md).
