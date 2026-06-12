# djlib-doctor

Read-only first, cue-safe DJ library verification and cleanup planning for Rekordbox exports, with staged Serato porting support.

`djlib-doctor` is an open-source toolkit for DJs who want to clean up a messy Rekordbox-oriented music library without losing hotcues, memory cues, playlist structure, or trust in their files. It starts with a deliberately boring foundation: verify a Rekordbox XML export, explain what is really in it, and produce reports that humans and coding agents can both understand.

The project is currently private and early. It is being prepared for eventual open-source release under [@pseudovirtual](https://github.com/pseudovirtual).

## Why This Exists

DJ libraries get weird in ways generic file dedupers do not understand:

- Rekordbox XML exports contain collection tracks and playlist references that look similar but mean different things.
- Streaming placeholders can appear next to real local files.
- A track can be duplicated across MP3, M4A, AIFF, WAV, FLAC, and dead paths.
- Hotcues and memory cues are creative work, not disposable metadata.
- A USB export can fail even when a track "looks" present.
- Blindly fixing paths, rewriting XML, or editing a database can make things worse.

`djlib-doctor` is designed around verification, dry-runs, transparent plans, and human review.

## Current Status

Implemented now:

- read-only Rekordbox XML parsing
- collection track counting separate from playlist reference counting
- local file vs streaming placeholder classification
- memory cue, hotcue, and loop parsing from `POSITION_MARK`
- human-readable verification report
- JSON verification report
- verification report file output
- verification schema version introspection
- suggested next actions in verification reports
- duplicate TrackID detection
- missing playlist reference detection
- unknown location warnings
- unknown cue type warnings
- read-only snapshot directory generation
- redacted shareable snapshots with portable artifact references
- read-only missing-files plan generation
- read-only duplicate plan generation
- duplicate collision policies: cue-safe, quality-first, or keep-both
- read-only cue coverage plan generation
- read-only bad path hygiene plan generation
- read-only audio compatibility plan generation from probe metadata CSV
- configurable audio compatibility profiles for Rekordbox, AIFF, WAV, and broad software libraries
- plan explanation
- interactive CLI review for plan decisions
- CSV decision-sheet export as an optional secondary review format
- dry-run-only apply manifest export
- schema discovery for JSON reports and CSV inputs/outputs
- baseline/final export comparison
- read-only Serato `root.sqlite` inspection
- dry-run Rekordbox XML playlist and playlist-file batch planning to Serato crate previews
- Serato legacy crate preview generation in an output folder
- staged Serato SQLite/crate updates from reviewed port manifests
- guarded Serato stage install with backups, hashes, sidecar checks, app-closed checks, and explicit confirmation tokens
- staged Serato audio tag writes for AIFF/AIF, M4A/MP4, and MP3 with backup/token install flow
- staged file copy, move, delete, and ffmpeg conversion operations from explicit manifests
- staged structured SQLite row operations for Rekordbox DB workflows
- synthetic XML fixture tests
- Codex and Claude project guidance files

Not implemented yet:

- Rekordbox XML writing
- Claude Desktop extension packaging
- public PyPI or GitHub release

## Safety Promise

The current project must not write to a Rekordbox database or real music library except through explicit staged install/apply commands with manifest files, backups, hashes, and confirmation tokens.

Future write-capable features must be built behind:

- dry-run manifests
- explicit user approval
- backups
- checksums or hashes where appropriate
- fixture tests
- final verification reports

No feature should be named or documented in a way that hides destructive behavior. There should never be a vague `fix my library` button.

## Quick Start For Developers

Run the current test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Run the read-only verifier against the synthetic fixture:

```bash
PYTHONPATH=src python3 -m djlib_doctor.cli verify tests/fixtures/rekordbox/simple.xml --no-file-check
PYTHONPATH=src python3 -m djlib_doctor.cli verify tests/fixtures/rekordbox/simple.xml --no-file-check --json --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli verify --schema-version
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml tests/fixtures/rekordbox/simple.xml --out work/snapshot-demo --no-file-check
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml tests/fixtures/rekordbox/simple.xml --out work/snapshot-redacted --no-file-check --redact-paths
PYTHONPATH=src python3 -m djlib_doctor.cli plan missing-files --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-duplicates.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-duplicates-quality.json --collision-policy quality
PYTHONPATH=src python3 -m djlib_doctor.cli plan bad-paths --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-bad-paths.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --list-profiles
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --probe-csv tests/fixtures/audio/compatibility_probes.csv --out work/snapshot-demo/plan-audio-compatibility.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --probe-csv tests/fixtures/audio/compatibility_probes.csv --out work/snapshot-demo/plan-wav-16.json --profile wav-16
PYTHONPATH=src python3 -m djlib_doctor.cli plan cues --baseline tests/fixtures/rekordbox/simple.xml --final tests/fixtures/rekordbox/simple.xml --out work/snapshot-demo/plan-cues.json
PYTHONPATH=src python3 -m djlib_doctor.cli explain --plan work/snapshot-demo/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli decision-sheet --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/decision-sheet.csv
PYTHONPATH=src python3 -m djlib_doctor.cli apply-manifest --plan work/snapshot-demo/plan-missing-files.json --review-log work/snapshot-demo/review-decisions.json --only-reviewed --out work/snapshot-demo/apply-manifest.json
PYTHONPATH=src python3 -m djlib_doctor.cli schema --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --playlist "ROOT / Fixture Playlist" --out work/serato-port-demo --verify-preview
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline tests/fixtures/rekordbox/simple.xml --final tests/fixtures/rekordbox/simple.xml
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline tests/fixtures/rekordbox/simple.xml --final tests/fixtures/rekordbox/simple.xml --check-files
```

After installing locally:

```bash
python3 -m pip install -e .
djlib-doctor verify tests/fixtures/rekordbox/simple.xml --no-file-check
```

Expected output:

```text
djlib-doctor verification: PASS
Source: tests/fixtures/rekordbox/simple.xml
File existence check: off
Collection tracks: 3
Playlist references: 2
Local file-backed tracks: 2
Streaming placeholders: 1
Unknown location tracks: 0
Missing local files: 0
Cues: 3 (2 hotcue, 1 memory, 1 loop)
Failures: 0
Warnings: 0

Suggested next actions:
- Create a snapshot before planning any cleanup or comparing this export to another export.
```

## Planned User Experience

For a DJ:

```bash
djlib-doctor verify ~/Desktop/rekordbox-export.xml
```

Then:

```text
No local files are missing.
866 streaming placeholders were found and ignored as local-file problems.
All parsed cue rows are accounted for.
2140 playlist references were counted separately from collection tracks.
```

Later milestones will add dry-run manifests for file operations, XML writing, and DB writing.

The `snapshot` command already exists:

```bash
djlib-doctor snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
djlib-doctor snapshot --rekordbox-xml export.xml --music-root ~/Music --out shareable-run/ --redact-paths
```

It writes `snapshot.json`, `verification.txt`, `verification.json`, `missing-files.csv`, `streaming-placeholders.csv`, `cue-summary.csv`, `playlist-summary.csv`, and, when a music root is provided, `filesystem-inventory.csv`. Redacted snapshots preserve filenames while hiding folder paths and use portable artifact filenames in `snapshot.json`.

The read-only plan commands also exist:

```bash
djlib-doctor plan missing-files --snapshot run/snapshot.json --out run/plan-missing-files.json
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates.json
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates-keep-both.json --collision-policy keep-both
djlib-doctor plan bad-paths --snapshot run/snapshot.json --out run/plan-bad-paths.json
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-audio-compatibility.json
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-aiff-24.json --profile rekordbox-aiff-24
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-custom-wav.json --allow-extension wav --allow-codec pcm_s16le --max-bit-depth 16
djlib-doctor plan cues --baseline baseline.xml --final final.xml --out run/plan-cues.json
djlib-doctor explain --plan run/plan-missing-files.json
djlib-doctor review --plan run/plan-missing-files.json --out run/review-decisions.json
djlib-doctor decision-sheet --plan run/plan-missing-files.json --out run/decision-sheet.csv
djlib-doctor apply-manifest --plan run/plan-missing-files.json --review-log run/review-decisions.json --only-reviewed --out run/apply-manifest.json
djlib-doctor schema plan --pretty
```

The Serato planning, staging, and guarded install commands also exist:

```bash
djlib-doctor inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / My Playlist" --crate-prefix "RB - " --out run/rb-to-serato --verify-preview
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --crate-prefix "RB - " --out run/rb-to-serato-batch
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --summary-only --out run/unused
djlib-doctor stage serato --port-manifest run/rb-to-serato/port-manifest.json --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --stage-dir run/serato-stage
djlib-doctor install serato-stage --stage-dir run/serato-stage --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --confirm-token "INSTALL_SERATO_STAGE:..."
djlib-doctor stage serato-tags --port-manifest run/rb-to-serato/port-manifest.json --stage-dir run/serato-tags
djlib-doctor install serato-tags --stage-dir run/serato-tags --confirm-token "INSTALL_SERATO_TAGS:..."
djlib-doctor stage rekordbox-db --db master.db --operations rekordbox-ops.json --stage-dir run/rb-db-stage
djlib-doctor install rekordbox-db --stage-dir run/rb-db-stage --db master.db --confirm-token "INSTALL_SQLITE_STAGE:..."
djlib-doctor stage file-ops --operations file-ops.json --stage-dir run/file-ops-stage
djlib-doctor install file-ops --stage-dir run/file-ops-stage --confirm-token "INSTALL_FILE_OPS:..."
```

The install commands write live files only after separate stages verify and exact stage tokens are supplied. Serato audio tags, Rekordbox SQLite row edits, and file copy/move/delete/convert operations are all explicit staged workflows, not side effects of planning.

The `compare exports` command can compare a baseline and final XML export:

```bash
djlib-doctor compare exports --baseline baseline.xml --final final.xml --out run/compare.json
djlib-doctor compare exports --baseline baseline.xml --final final.xml --out run/compare-with-files.json --check-files
```

The tool should always explain what it found before it proposes what to do.

## Documentation

- [Feature List](docs/feature-list.md)
- [Execution Plan](docs/execution-plan.md)
- [Human Workflows](docs/human-workflows.md)
- [Legacy Script Audit](docs/legacy-script-audit.md)
- [Serato Porting](docs/serato-porting.md)
- [GitHub Launch Plan](docs/github-launch-plan.md)
- [Agent Friendliness And Discovery](docs/agent-friendliness-and-discovery.md)
- [Initial Milestone](outputs/initial_milestone.md)
- [llms.txt](llms.txt)

## Agent Support

This repo includes:

- `AGENTS.md` for Codex-style agents
- `CLAUDE.md` for Claude-style project context
- a future plan for a Codex skill/plugin
- a future plan for a Claude Desktop extension package

The near-term agent strategy does **not** include building a standalone MCP server. Claude Desktop packaging is allowed later as an install/distribution surface once the CLI is stable.

## Roadmap

1. XML Verifier Alpha
2. Human-readable and JSON reports
3. Snapshot command
4. Fixture corpus expansion
5. Plan generation for missing paths, duplicates, cues, and playlists
6. Baseline/final comparison verification
7. Codex skill and plugin packaging
8. Claude Desktop extension packaging
9. Safe file operations with dry-run manifests
10. Rekordbox XML writer
11. Rekordbox database writer with backups and guards
12. Cross-platform adapters

## Contributing

This project is not public yet. Before public release, the repo should have:

- final license review
- contributing guide
- code of conduct
- issue templates
- fixture policy
- safety policy
- release checklist
- CI running tests

Good early contributions are synthetic fixtures, report examples, parser tests, and documentation that helps DJs understand what the tool is saying.

## Trademark

Rekordbox is a trademark of AlphaTheta/Pioneer DJ. This project is not affiliated with or endorsed by AlphaTheta/Pioneer DJ.
