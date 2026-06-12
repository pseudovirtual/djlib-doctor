# Safety Policy

`djlib-doctor` is read-only first.

## Current Rule

The current code must not:

- write to a Rekordbox database except through staged SQLite operations with exact confirmation tokens
- write to a live Serato database except through `install serato-stage` after a verified stage, backup, sidecar check, app-closed check, and exact confirmation token
- modify a Rekordbox XML export
- modify Serato audio tags
- move music files except through staged file operations with exact confirmation tokens
- rename music files
- convert audio files except through staged file operations with exact confirmation tokens
- quarantine files
- delete files except through staged file operations with exact confirmation tokens

## Future Write-Capable Rule

Future write-capable features must require:

- explicit command names
- dry-run output first
- manifest file
- human-readable explanation
- user approval
- backup or rollback path
- verification after action

## Current Serato Install Rule

The Serato install workflow is intentionally narrow:

- `port rb-to-serato` writes dry-run manifests and preview crates
- `stage serato` copies live `root.sqlite` into a stage folder and modifies only the staged copy
- `install serato-stage` installs the staged `root.sqlite` and staged crate files only after the stage verifies
- live audio files and Serato audio tags are never modified

The install command must:

- require the exact `install_token` from `serato-stage-manifest.json`
- refuse if Serato appears to be running
- refuse if SQLite sidecars exist beside live `root.sqlite`
- back up live `root.sqlite` and overwritten crate files
- hash-check installed files against staged files
- write `serato-install-report.json`

## Implemented Guard Utilities

The codebase includes safety utilities for future write-capable milestones:

- detect Rekordbox SQLite sidecars such as `master.db-wal` and `master.db-shm`
- detect Serato SQLite sidecars such as `root.sqlite-wal`, `root.sqlite-shm`, and `root.sqlite-journal`
- check mocked or captured process listings for running Rekordbox or Serato apps before future staged installs
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
