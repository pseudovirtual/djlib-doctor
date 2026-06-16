# Security And Safety

`djlib-doctor` is designed for local DJ library verification, planning, staging, and token-gated installs.

## Reporting Issues

Use GitHub issues for ordinary bugs. For security-sensitive reports, use GitHub private vulnerability reporting if enabled.

## Current Risk Boundary

Planning commands are read-only with respect to Rekordbox databases, Serato databases, audio tags, and music files.

It may read:

- Rekordbox XML exports selected by the user
- Rekordbox and Serato database files selected by the user
- local file paths referenced by those exports

It must not:

- edit a live database outside a token-gated `install ...` command
- edit an XML export
- move files outside `install file-ops`
- convert files outside `install file-ops`
- delete files outside `install file-ops`
- write Serato audio tags outside `install serato-tags`

## Privacy

Do not share private Rekordbox exports, real music files, or personal library paths in public issues.
