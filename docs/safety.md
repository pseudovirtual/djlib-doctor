# Safety Policy

`djlib-doctor` is read-only first.

## Current Rule

The current code must not:

- write to a Rekordbox database
- write to a live Serato database
- modify a Rekordbox XML export
- modify Serato audio tags
- move music files
- rename music files
- convert audio files
- quarantine files
- delete files

## Future Write-Capable Rule

Future write-capable features must require:

- explicit command names
- dry-run output first
- manifest file
- human-readable explanation
- user approval
- backup or rollback path
- verification after action

## Implemented Guard Utilities

The codebase includes safety utilities for future write-capable milestones:

- detect Rekordbox SQLite sidecars such as `master.db-wal` and `master.db-shm`
- detect Serato SQLite sidecars such as `root.sqlite-wal`, `root.sqlite-shm`, and `root.sqlite-journal`
- generate timestamped backup paths
- aggregate safety check status

These utilities do not write to the database and do not enable DB patching. They exist so future write modules reuse tested guard logic.

## Naming Rule

Commands should say what they do.

Good:

- `plan missing-files`
- `plan duplicates`
- `plan bad-paths`
- `plan cues`
- `apply-file-plan`
- `quarantine-files`

Bad:

- `fix`
- `clean`
- `repair everything`

## Fixture Rule

Tests should use synthetic fixtures.

Do not commit:

- real Rekordbox exports
- real music metadata from private libraries
- proprietary database files
- user music files
