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
- **Certify migrations:** generated previews and staged artifacts should be scored before install.
- **Fingerprint honestly:** base fingerprinting compares raw file bytes; acoustic identity belongs behind a future optional backend.

## Command Shape

Manual flow:

```bash
djlib-doctor verify export.xml
djlib-doctor fingerprint compare copy-a.wav copy-b.wav --out run/file-compare.json
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Test" --out run/port
djlib-doctor certify rb-to-serato --port-manifest run/port/port-manifest.json --out run/port/certification.json
djlib-doctor stage serato --port-manifest run/port/port-manifest.json --serato-library-dir ~/serato-library --serato-music-dir ~/_Serato_ --stage-dir run/serato-stage
djlib-doctor stage serato-tags --port-manifest run/port/port-manifest.json --stage-dir run/serato-tags
djlib-doctor port serato-to-rb --serato-library-dir ~/serato-library --crate ~/Music/_Serato_/Subcrates/Test.crate --collection-root ~/Music --out run/serato-to-rb
djlib-doctor certify serato-to-rb --port-manifest run/serato-to-rb/port-manifest.json --out run/serato-to-rb/certification.json
djlib-doctor stage rekordbox-db-import --db ~/Library/Pioneer/rekordbox/master.db --port-manifest run/serato-to-rb/port-manifest.json --stage-dir run/rekordbox-stage
djlib-doctor install rekordbox-db --stage-dir run/rekordbox-stage --db ~/Library/Pioneer/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
```

Workflow shortcut:

```bash
djlib-doctor sync plan --config run/djlib-doctor.json --collection --out run/sync-plan
djlib-doctor sync --config run/djlib-doctor.json --collection --out run/sync-run --apply --yes
djlib-doctor migrate rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Test" --out run/migrate --stage-library --stage-tags --serato-library-dir ~/serato-library --serato-music-dir ~/_Serato_
djlib-doctor migrate serato-to-rb --serato-library-dir ~/serato-library --crate ~/Music/_Serato_/Subcrates/Test.crate --collection-root ~/Music --out run/serato-to-rb --stage-db --rekordbox-db ~/Library/Pioneer/rekordbox/master.db
```

Serato-to-Rekordbox produces a port manifest and Rekordbox XML representation, then can stage supported plain-SQLite or pyrekordbox-readable encrypted DB imports into a copied Rekordbox `master.db` for token-gated install. Real captured DB certification is still pending.

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

The next major gap is real-world certification coverage: anonymized fixture bundles across app versions, real Rekordbox DB schema adapters, playlist table imports, additional Serato marker/tag fixtures, and an optional acoustic fingerprint backend. New support should extend the existing core model and staged workflow rather than introducing parallel migration code.
