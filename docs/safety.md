# Safety Policy

`djlib-doctor` is read-only first.

## Current Rule

The current code must not:

- write to a Rekordbox database except through staged SQLite operations with exact confirmation tokens
- write to a live Serato database except through `install serato-stage` after a verified stage, backup, sidecar check, app-closed check, and exact confirmation token
- modify a Rekordbox XML export
- modify Serato audio tags except through `install serato-tags` after a verified stage and exact confirmation token
- move music files except through staged file operations with exact confirmation tokens
- rename music files
- convert audio files except through staged file operations with exact confirmation tokens
- quarantine files
- delete files except through staged file operations with exact confirmation tokens

Staged file operations are all-or-nothing by default. If one operation fails, previously applied file copies, moves, converts, or deletes are rolled back from stage-local backups. `install file-ops --continue-on-error` is available for explicit partial-apply workflows and records errors in the install report.

Convert operations require `ffmpeg` on `PATH` at staging time. If it is missing, staging fails before any staged convert output is produced.

## Write-Capable Rule

Write-capable features must require:

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
- live audio files and Serato audio tags are modified only by explicit token-gated install commands

The install command must:

- require the exact `install_token` from `serato-stage-manifest.json`
- recompute the install token from the manifest contents before writing
- refuse if the live `root.sqlite` hash changed after staging
- refuse if Serato appears to be running
- refuse if SQLite sidecars exist beside live `root.sqlite`
- back up live `root.sqlite` and overwritten crate files
- hash-check installed files against staged files
- write `serato-install-report.json`

## Current Rekordbox DB Install Rule

The Rekordbox DB workflow is intentionally staged:

- never write a live `master.db` directly
- copy `master.db` into a stage directory first
- apply only manifest-described operations to the staged copy
- verify SQLite integrity before and after staged operations
- install only through `install rekordbox-db`
- require token, source hash, staged hash, backup, sidecar checks, and app-closed checks

Serato-to-Rekordbox should use that staged DB path. XML preview is a representation and inspection artifact, not the final write workflow.

## Implemented Guard Utilities

The codebase includes safety utilities for future write-capable milestones:

- detect Rekordbox SQLite sidecars such as `master.db-wal` and `master.db-shm`
- detect Serato SQLite sidecars such as `root.sqlite-wal`, `root.sqlite-shm`, and `root.sqlite-journal`
- check mocked or captured process listings for running Rekordbox or Serato apps before staged installs
- generate timestamped backup paths
- aggregate safety check status

These utilities support staged write modules; they do not justify bypassing stage/install boundaries.

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
