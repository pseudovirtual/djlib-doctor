# GitHub Launch Plan

Historical note: this was the pre-public launch checklist. The repository is now public, so use this archived file only as historical context and do not follow the private-repo setup commands as current instructions.

This project should eventually live at:

```text
https://github.com/pseudovirtual/djlib-doctor
```

The repo is now public at that location.

## Repository Setup Checks

Before publishing or changing repository settings:

- confirm `gh auth status`
- confirm no private music data is present
- confirm no real Rekordbox exports are committed
- confirm no absolute user-library paths are in fixtures
- confirm tests pass

## Files To Add Before Public Release

Required:

- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `.gitignore`
- `.github/workflows/tests.yml`
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/fixture_request.md`
- `.github/pull_request_template.md`

Recommended:

- `docs/safety.md`
- `docs/reports.md`
- `docs/rekordbox-xml-concepts.md`
- `docs/legacy-script-audit.md`
- `examples/reports/`
- `llms.txt` (done)
- `llms-full.txt` (done)

## Repository Description

Suggested GitHub description:

```text
Read-only first, cue-safe DJ library verification and cleanup planning for Rekordbox exports.
```

## Topics

Suggested topics:

- `rekordbox`
- `dj`
- `music-library`
- `hotcues`
- `cue-points`
- `xml`
- `library-cleanup`
- `agent-tools`
- `codex`
- `claude-desktop`

## Public README Requirements

The public README should include:

- clear status badge
- one-sentence pitch
- screenshot or sample report
- safety promise
- install instructions
- first command
- explanation of output
- feature list
- roadmap
- contribution links
- trademark note

## Privacy Scrub Checklist

Before making public:

- search for private home-directory paths
- search for private music filenames
- search for real artist/title metadata from private exports
- search for cloud-drive folder names, Rekordbox database paths, or USB names from private work
- search for one-off playlist names and TrackID overrides from private work
- verify fixtures are synthetic
- verify docs do not imply affiliation with AlphaTheta/Pioneer DJ

Suggested commands:

```bash
rg "<private-username>|<private-folder>|<private-export-name>|<private-db-path>|<private-project-name>"
PYTHONPATH=src python3 -m unittest discover -s tests
```

## First Public Release Scope

Include:

- read-only XML verifier
- fixture tests
- human report
- JSON report if ready
- docs
- Codex/Claude guidance files

Exclude:

- file operations
- DB writes
- real user library examples
- automatic cleanup
- broad claims about supporting all DJ platforms

## Release Messaging

Tone:

- careful
- transparent
- DJ-friendly
- no magic claims

Suggested launch phrasing:

```text
I’m building djlib-doctor, a read-only-first toolkit for understanding and eventually cleaning up Rekordbox DJ libraries without losing cue work. The first release verifies Rekordbox XML exports, distinguishes real local files from streaming placeholders, and explains confusing XML counts.
```
