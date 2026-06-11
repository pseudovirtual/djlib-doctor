# Security And Safety

`djlib-doctor` is designed for local DJ library verification.

## Reporting Issues

While the project is private, report issues directly in the private repository.

After public release, use GitHub issues for ordinary bugs. For security-sensitive reports, use GitHub private vulnerability reporting if enabled.

## Current Risk Boundary

The current code is read-only with respect to Rekordbox databases and music libraries.

It may read:

- Rekordbox XML exports selected by the user
- local file paths referenced by those exports

It must not currently:

- edit a database
- edit an XML export
- move files
- convert files
- delete files

## Privacy

Do not share private Rekordbox exports, real music files, or personal library paths in public issues.
