# djlib-doctor

Read-only-first, cue-safe DJ library verification and migration planning for Rekordbox and Serato.

`djlib-doctor` helps DJs and coding agents inspect messy libraries, plan cleanup, compare exports, and stage migrations without silently rewriting creative metadata. It treats hotcues, memory cues, loops, playlist order, and source files as things to verify before touching.

This repo is currently private and being prepared for eventual open-source release under [@pseudovirtual](https://github.com/pseudovirtual).

## What It Does

- verifies Rekordbox XML exports
- separates collection tracks from playlist references
- treats streaming placeholders as placeholders, not missing files
- parses memory cues, hotcues, cue loops, and loop end times
- creates snapshots and redacted shareable reports
- plans missing-file, duplicate, cue, bad-path, and audio-format cleanup
- supports duplicate policies: `cue-safe`, `quality`, and `keep-both`
- records interactive review decisions
- compares baseline/final exports for lost material or cue regressions
- dry-runs Rekordbox-to-Serato and Serato-to-Rekordbox migrations
- stages Serato library updates, Serato audio tags, file operations, and SQLite operations behind explicit install tokens

## Safety Model

Planning commands do not write to live libraries. Write-capable flows are split into explicit `stage ...` and `install ...` commands. Install commands verify:

- exact confirmation token
- token recomputed from manifest contents
- staged file hashes
- live source hashes from staging time
- backups
- app/SQLite sidecar checks where relevant

There is no vague `fix my library` command.

## Quick Start

```bash
python3 -m pip install -e .
djlib-doctor verify tests/fixtures/rekordbox/simple.xml --no-file-check
djlib-doctor self-test
```

Run the full suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src PYTHONPYCACHEPREFIX=work/pycache python3 -m compileall -q src tests
```

## Common Workflows

```bash
djlib-doctor snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
djlib-doctor plan missing-files --snapshot run/snapshot.json --out run/missing.json
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/dupes.json --collision-policy cue-safe
djlib-doctor review --plan run/missing.json --out run/review.json
djlib-doctor compare exports --baseline before.xml --final after.xml --out run/compare.json
```

Rekordbox to Serato dry-run:

```bash
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Set" --out run/port --verify-preview
```

Serato to Rekordbox dry-run:

```bash
djlib-doctor port serato-to-rb --serato-library-dir Library --crate Set.crate --collection-root ~/Music --out run/rb
```

Staged Serato install:

```bash
djlib-doctor stage serato --port-manifest run/port/port-manifest.json --serato-library-dir Library --serato-music-dir _Serato_ --stage-dir run/stage
djlib-doctor install serato-stage --stage-dir run/stage --serato-library-dir Library --serato-music-dir _Serato_ --confirm-token INSTALL_SERATO_STAGE:...
```

## Project Status

Implemented: verification, snapshots, cleanup plans, review logs, schema output, export comparison, Serato inspection, two-way dry-run porting, and staged/token-gated install workflows.

Still pre-release: Rekordbox XML writing, public packaging, CI/release automation, and broader real-world Serato cue/tag fixture validation.

## More Docs

- [Safety](docs/safety.md)
- [Feature List](docs/feature-list.md)
- [Serato Porting](docs/serato-porting.md)
- [Agent Friendliness](docs/agent-friendliness-and-discovery.md)
- [Architecture](docs/product-architecture.md)
