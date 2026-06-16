# Product Architecture

`djlib-doctor` should feel like a small toolkit, not a maze of scripts.

## Product Goal

Help DJs safely move and maintain local DJ libraries across apps:

- Rekordbox to Serato
- Serato to Rekordbox
- format conversion without losing cues
- playlist, crate, cue, loop, and metadata preservation
- staged writes with human approval

Streaming placeholders are treated as non-local references. The tool can report them, but local file workflows should not try to edit or migrate streaming-provider data.

## Design Principles

- **Small core model:** tracks, playlists, cues, loops, audio files, and platform IDs.
- **Adapters at the edges:** Rekordbox XML/DB and Serato SQLite/crates/tags should translate into and out of the core model.
- **Plan before write:** every mutation starts as a manifest.
- **Stage before install:** live files are touched only by install/apply commands.
- **One safety vocabulary:** hashes, backups, sidecar checks, app-closed checks, and exact install tokens.
- **Agent-friendly outputs:** JSON manifests and schemas for every important artifact.
- **Human-friendly commands:** common workflows get short commands; low-level steps remain available.

## Command Shape

Manual flow:

```bash
djlib-doctor verify export.xml
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Test" --out run/port
djlib-doctor stage serato --port-manifest run/port/port-manifest.json --serato-library-dir ~/serato-library --serato-music-dir ~/_Serato_ --stage-dir run/serato-stage
djlib-doctor stage serato-tags --port-manifest run/port/port-manifest.json --stage-dir run/serato-tags
djlib-doctor port serato-to-rb --serato-library-dir ~/serato-library --crate ~/Music/_Serato_/Subcrates/Test.crate --collection-root ~/Music --out run/serato-to-rb
djlib-doctor stage rekordbox-db --db ~/Library/Pioneer/rekordbox/master.db --operations run/rekordbox-db-operations.json --stage-dir run/rekordbox-stage
```

Workflow shortcut:

```bash
djlib-doctor migrate rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Test" --out run/migrate --stage-library --stage-tags --serato-library-dir ~/serato-library --serato-music-dir ~/_Serato_
djlib-doctor migrate serato-to-rb --serato-library-dir ~/serato-library --crate ~/Music/_Serato_/Subcrates/Test.crate --collection-root ~/Music --out run/serato-to-rb
```

Serato-to-Rekordbox currently produces a port manifest and Rekordbox XML representation. The final target architecture is a high-level stage command that imports that manifest/XML representation into a copied Rekordbox `master.db`, then installs it through the existing token-gated `install rekordbox-db` path.

Fast smoke test:

```bash
djlib-doctor self-test
```

## Extensibility Path

Add platforms by implementing adapters, not by copying workflows:

- read platform data into the core model
- write a dry-run port manifest from core model data
- stage platform-specific writes from the manifest
- install staged files with shared safety helpers

The next major gap is the Serato-to-Rekordbox staged DB import wrapper. It should reuse the core model and staged SQLite workflow rather than introducing parallel migration code.
