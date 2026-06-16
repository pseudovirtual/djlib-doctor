# Changelog

## Unreleased

- [x] P0.1: Added Serato Markers2 golden-vector tests for hotcue and saved-loop parsing.
- [x] Backlog 1: Rescoped fingerprinting as exact-duplicate/raw-byte similarity instead of audio identity.
- [x] Backlog 2: Added adversarial Serato install refusal tests and hardened stage manifest/backup verification.
- [x] Backlog 3: Documented Rekordbox DB import support boundaries and added a clear encrypted SQLCipher refusal.
- [x] Backlog 4: Moved limited-coverage claims out of README present-tense feature lists.
- [x] Backlog 5: Consolidated directional port workflow modules into their public modules.
- [x] Backlog 6: Added Serato Markers2 fidelity coverage for cue/loop positions, slots, and playlist order.
- Added read-only Rekordbox XML parser.
- Added cue parsing for memory cues, hotcues, and loops.
- Added verification report counts.
- Added JSON verification reports.
- Added duplicate TrackID and missing playlist reference failures.
- Added unknown location and unknown cue type warnings.
- Extracted shared location parsing utilities.
- Added read-only `snapshot` command with JSON, text, CSV, and optional filesystem inventory artifacts.
- Added read-only `plan missing-files` and `explain --plan` commands.
- Added read-only `plan duplicates` command.
- Added read-only `plan cues` command based on baseline/final comparison issues.
- Added read-only `compare exports` command for baseline/final XML verification.
- Added interactive `review`, dry-run `apply-manifest`, and schema discovery commands.
- Added read-only Serato `root.sqlite` inspection.
- Added dry-run Rekordbox XML to Serato port manifests and Serato crate previews.
- Expanded Serato dry-runs with playlist-file batches, summary-only mode, preview verification, cue-count metrics, format capability notes, and namespace warnings.
- Added staged Serato SQLite/crate install workflow with stage manifests, verification, install tokens, backups, sidecar checks, app-closed checks, and hash verification.
- Added staged Serato audio tag writes, structured Rekordbox SQLite row operations, and file copy/move/delete/convert operations behind manifest/token workflows.
- Added staged Serato-to-Rekordbox DB imports with fixture-backed cue rows for supported Rekordbox schemas.
- Added repo-scoped Codex skill and plugin skeleton.
- Added Claude Desktop extension template with explicit non-installable status.
- Added shared safety guard utilities for staged write workflows.
- Added `llms.txt` and `llms-full.txt` for model discoverability.
- Added synthetic fixture tests.
- Added Codex and Claude guidance files.
- Added open-source execution and GitHub launch plans.
