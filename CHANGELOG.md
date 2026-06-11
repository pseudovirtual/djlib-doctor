# Changelog

## Unreleased

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
- Added repo-scoped Codex skill and plugin skeleton.
- Added Claude Desktop extension template with explicit non-installable status.
- Added safety guard utilities for future DB-write milestones.
- Added `llms.txt` and `llms-full.txt` for future model discoverability.
- Added synthetic fixture tests.
- Added Codex and Claude guidance files.
- Added open-source execution and GitHub launch plans.
