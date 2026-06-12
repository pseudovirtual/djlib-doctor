# Feature List

This file describes what `djlib-doctor` should become, in language that both DJs and developers can understand.

## Available Now

### Rekordbox XML Verification

Reads a Rekordbox XML export without modifying it.

Current checks:

- counts collection tracks
- counts playlist references separately from collection tracks
- classifies local file-backed tracks
- classifies streaming placeholders
- classifies unknown locations
- reports missing local files when file checking is enabled
- reports duplicate collection TrackIDs
- reports playlist references to missing collection TrackIDs
- warns on unknown locations
- warns on unknown cue types
- parses memory cues
- parses hotcue slots
- parses loop cues
- renders human-readable and JSON output
- writes verification reports with `--out`
- prints the verification schema version with `--schema-version`
- includes source metadata and suggested next actions

### Synthetic Fixture Tests

The test suite uses fake Rekordbox XML, not private user music.

Fixture coverage currently includes:

- local file track
- missing file track
- streaming placeholder
- playlist references
- memory cue
- hotcue A
- loop cue
- bad active folder reference

### Agent Guidance

The repo includes project-level guidance files:

- `AGENTS.md` for Codex
- `CLAUDE.md` for Claude-oriented sessions

These files tell agents to stay read-only and preserve cue semantics.

### Snapshot Command

Creates a read-only artifact directory:

```bash
djlib-doctor snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
djlib-doctor snapshot --rekordbox-xml export.xml --music-root ~/Music --out shareable-run/ --redact-paths
```

Current artifacts:

- `snapshot.json`
- `verification.txt`
- `verification.json`
- `missing-files.csv`
- `streaming-placeholders.csv`
- `cue-summary.csv`
- `playlist-summary.csv`
- `filesystem-inventory.csv` when `--music-root` is provided

Current behavior:

- includes command metadata in `snapshot.json`
- keeps artifact references portable inside `snapshot.json`
- supports `--redact-paths` for shareable snapshots
- preserves filenames while hiding folder paths
- redacts paths in verification reports, track summaries, missing-file rows, streaming locations, and filesystem inventory

### Missing Files Plan

Builds a conservative read-only plan from a snapshot:

```bash
djlib-doctor plan missing-files --snapshot run/snapshot.json --out run/plan-missing-files.json
djlib-doctor explain --plan run/plan-missing-files.json
```

Current behavior:

- marks cue-bearing playlist-used missing records as unsafe reacquire/manual-match rows
- marks playlist-used missing records as unsafe reacquire/manual-match rows
- marks unreferenced missing records as review-only removal candidates
- marks same-stem filesystem candidates as weak review candidates
- never applies changes

### Duplicate Plan

Builds a conservative read-only duplicate plan from a snapshot:

```bash
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates.json
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates-quality.json --collision-policy quality
```

Current behavior:

- groups duplicate records by normalized artist/title
- recommends a survivor using the selected collision policy
- supports `cue-safe`, `quality`, and `keep-both` collision policies
- defaults to `cue-safe`, which prefers cue-bearing and playlist-referenced records before file quality
- `quality` prefers more compatible/higher-quality local files while flagging cue migration risks
- `keep-both` marks duplicate records as intentional review rows rather than removal candidates
- marks multiple cued duplicate groups as unsafe review rows
- marks non-survivors as review-only remove-later candidates
- records the collision policy in plan action metadata
- never applies changes

### Cue Coverage Plan

Builds a conservative read-only cue plan from baseline/final compare issues:

```bash
djlib-doctor plan cues --baseline baseline.xml --final final.xml --out run/plan-cues.json
```

Current behavior:

- turns uncovered baseline cue times into review rows
- turns hotcue regressions into unsafe review rows
- never writes cues

### Bad Path Hygiene Plan

Builds a conservative read-only plan for local tracks that point at bad, staging, temp, quarantine, or custom folder markers:

```bash
djlib-doctor plan bad-paths --snapshot run/snapshot.json --out run/plan-bad-paths.json
djlib-doctor plan bad-paths --snapshot run/snapshot.json --out run/plan-bad-paths.json --marker rejects
```

Current behavior:

- scans snapshot track summaries, not the live music library
- ignores streaming placeholders
- flags only folder-name markers, not vague substring matches
- marks cue-bearing or playlist-referenced rows as unsafe human-review items
- supports repeated custom `--marker` values
- never moves, deletes, or edits files

### Audio Compatibility Plan

Builds a conservative read-only review plan from audio probe metadata:

```bash
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-audio-compatibility.json
djlib-doctor plan audio-compatibility --list-profiles
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-wav-16.json --profile wav-16
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/custom.json --allow-extension aiff --allow-codec pcm_s24be --max-bit-depth 24
```

Current behavior:

- consumes CSV metadata instead of probing files directly
- defaults to `rekordbox-conservative`, a recommendation rather than an official hardware spec
- includes named profiles: `rekordbox-conservative`, `rekordbox-aiff-16`, `rekordbox-aiff-24`, `wav-16`, `wav-24`, and `broad-software-library`
- supports CLI overrides for allowed extensions, allowed codecs, max sample rate, max bit depth, and low-bitrate warning threshold
- checks extension, codec, sample rate, bit depth, duration, bit rate, and probe success
- flags ALAC-in-M4A separately from AAC-in-M4A
- flags FLAC and high sample-rate files under the conservative profile
- turns failures and warnings into human-review plan rows
- never converts or modifies audio

Future cue-collision policies should support preferences such as keep better cues, keep later cues, demote losing hotcues to memory cues, or keep both cue sets. Those require reliable cue edit metadata before any write-capable workflow can safely apply them.

### Baseline/Final Export Compare

Compares two Rekordbox XML exports:

```bash
djlib-doctor compare exports --baseline baseline.xml --final final.xml --out run/compare.json
djlib-doctor compare exports --baseline baseline.xml --final final.xml --out run/compare-with-files.json --check-files
```

Current checks:

- material tracks represented by normalized artist/title
- cue coverage by cue time tolerance
- hotcue count regression
- playlist entry/order projection by normalized artist/title
- final bad/staging path references
- final missing local file status when `--check-files` is provided

### Interactive Review

Walks a generated plan row by row and records human decisions:

```bash
djlib-doctor review --plan run/plan-missing-files.json --out run/review-decisions.json
djlib-doctor decision-sheet --plan run/plan-missing-files.json --out run/decision-sheet.csv
```

Current behavior:

- prompts repeatedly down the plan list
- offers decision choices tailored to the plan type
- records notes and the original plan action payload
- writes ingestible `review-decisions.json`
- optionally writes CSV decision sheets for spreadsheet review
- never applies the decisions

### Schema Discovery

Prints machine-readable report and CSV schema metadata:

```bash
djlib-doctor schema --pretty
djlib-doctor schema plan --pretty
```

Current behavior:

- lists verification, snapshot, plan, compare, review-log, decision-sheet, apply-manifest, and audio-probe CSV contracts
- exposes schema versions and important fields
- avoids adding runtime validation dependencies

### Serato Inspection

Reads Serato `Library/root.sqlite` without modifying it:

```bash
djlib-doctor inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato
```

Current behavior:

- opens SQLite in read-only mode
- reports tables, columns, row counts, and schema fingerprint
- writes `serato-inspection.json`
- never writes to the Serato library

### Rekordbox XML To Serato Dry-Run Port

Builds a dry-run Serato crate plan from Rekordbox XML playlists:

```bash
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / My Playlist" --crate-prefix "RB - " --out run/rb-to-serato
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --crate-prefix "RB - " --out run/rb-to-serato-batch
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --summary-only --out run/unused
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / My Playlist" --out run/rb-to-serato --verify-preview
```

Current behavior:

- writes `port-manifest.json`
- writes Serato legacy `.crate` previews in the output folder
- writes `unsupported.csv`
- reuses the neutral library model used by Rekordbox parsing
- maps hotcue, memory cue, and loop intent for Serato
- supports one playlist or a text file of playlists
- supports summary-only dry runs
- verifies single-crate preview order against the manifest with `--verify-preview`
- reports raw Rekordbox cue rows, unique per-track cues, and Serato-writable cue slots
- reports Serato cue-tag capability by audio extension
- records a managed crate namespace policy
- warns on trim-only playlist matches and sanitized crate filename collisions
- skips non-local placeholder tracks
- never writes live Serato SQLite files or audio tags

### Serato Stage And Guarded Install

Stages and installs Serato SQLite/crate changes from a reviewed port manifest:

```bash
djlib-doctor stage serato --port-manifest run/rb-to-serato/port-manifest.json --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --stage-dir run/serato-stage
djlib-doctor install serato-stage --stage-dir run/serato-stage --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --confirm-token "INSTALL_SERATO_STAGE:..."
```

Current behavior:

- stages changes into copied `root.sqlite`, never the live database
- writes staged crate files under the stage directory
- writes `serato-stage-manifest.json` with hashes and an install token
- writes `serato-stage-verification.json`
- requires exact install token for live install
- refuses install if Serato appears to be running
- refuses install if live SQLite sidecars exist
- backs up live `root.sqlite` and overwritten crate files
- verifies installed file hashes
- writes `serato-install-report.json`
- does not write Serato audio tags; use `stage serato-tags` for the separate audio-tag workflow

### Serato Audio Tag Stage And Install

Stages and installs Serato cue/loop tag writes from a port manifest:

```bash
djlib-doctor stage serato-tags --port-manifest run/rb-to-serato/port-manifest.json --stage-dir run/serato-tags
djlib-doctor install serato-tags --stage-dir run/serato-tags --confirm-token "INSTALL_SERATO_TAGS:..."
```

Current behavior:

- stages tagged audio-file copies before touching originals
- supports AIFF/AIF, M4A/MP4, and MP3 when `djlib-doctor[audio-tags]` is installed
- records unsupported formats or missing dependencies in the stage manifest
- backs up originals before install
- requires exact install token

### Generic Staged Write Operations

Supports explicit manifest-backed write workflows:

```bash
djlib-doctor stage rekordbox-db --db master.db --operations rekordbox-ops.json --stage-dir run/rb-db-stage
djlib-doctor install rekordbox-db --stage-dir run/rb-db-stage --db master.db --confirm-token "INSTALL_SQLITE_STAGE:..."
djlib-doctor stage file-ops --operations file-ops.json --stage-dir run/file-ops-stage
djlib-doctor install file-ops --stage-dir run/file-ops-stage --confirm-token "INSTALL_FILE_OPS:..."
```

Current behavior:

- stages structured SQLite insert/update/delete operations on a DB copy
- stages file copy, move, delete, and ffmpeg conversion operations
- requires install tokens
- creates backups before live mutation
- verifies staged hashes

### Dry-Run Apply Manifest

Writes an inert apply manifest from any generated plan:

```bash
djlib-doctor apply-manifest --plan run/plan-missing-files.json --review-log run/review-decisions.json --only-reviewed --out run/apply-manifest.json
```

Current behavior:

- sets `mode` to `dry_run_only`
- records proposed operations and evidence
- can ingest `review-decisions.json`
- marks every operation as `not_applied`
- requires explicit future approval, backup, and post-apply verification
- never applies changes

## Near-Term Features

### Better Human Reports

Reports should answer DJ questions directly:

- "Do I have missing local files?"
- "How many records are streaming placeholders?"
- "Why does the XML have more tracks than Rekordbox shows?"
- "How many cues did the tool parse?"
- "Which playlists reference missing collection tracks?"

### JSON Reports

Every human report should have a machine-readable form:

```bash
djlib-doctor verify export.xml --json
```

JSON reports should include:

- schema version
- counts
- warnings
- failures
- source file path
- next recommended command

Still to add:

- richer command metadata

### Snapshot Command Enhancements

Create a read-only snapshot of the current situation:

```bash
djlib-doctor snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
```

Snapshot output should include:

- playlist summary
- richer source metadata
- optional path redaction for shareable snapshots (done)

### Fixture Corpus

Add synthetic fixture categories:

- clean library
- missing local file
- streaming placeholder
- missing file with compatible equivalent
- missing cue-bearing file with no equivalent
- duplicate file formats
- unsafe remix collision
- duplicate group where cue-bearing record must survive
- duplicate group with multiple cued records and different cue signatures
- playlist order projection
- playlist reference to missing TrackID
- cue union without conflict
- cue union with hotcue slot conflict
- near-zero placeholder hotcue
- loop cue
- cue shift
- format replacement
- reacquire-needed track
- bad active folder reference
- temp staging file
- superseded backup file
- referenced incompatible file with clean equivalent
- non-audio artifact in music folder

## Planning Features

Planning means producing a dry-run proposal, not changing anything.

Planned commands:

```bash
djlib-doctor explain --plan run/duplicates-plan.json
```

Plans should explain:

- what would change
- why the tool thinks it is safe
- what evidence was used
- match confidence
- human-review requirements
- what needs human review
- what would be verified afterward

### Match Evidence And Confidence

The planner should classify match evidence instead of treating every candidate equally.

Evidence types:

- same path
- exact file hash
- same XML TrackID
- same artist/title
- same normalized filename stem
- close duration
- same acoustic feature
- same playlist context
- same source-folder context

Confidence levels:

- exact
- strong
- candidate
- weak
- unsafe

Weak and unsafe matches should generate review rows, not automatic repair actions.

### Human Review Workbooks

Large DJ libraries need decision sheets, not just terminal output.

Future report families:

- verification report
- snapshot report
- candidate plan
- human decision sheet
- apply manifest
- post-apply audit

CSV and JSON should come first. XLSX export can come later for DJs reviewing large plans.

### Playlist Projection Verification

Compare a baseline playlist to a final or planned playlist after applying TrackID mappings.

Checks:

- playlist exists
- projected entries exist
- order is preserved
- duplicate occurrence policy is honored
- intentionally superseded playlists are declared

### Cue Coverage Verification

Compare source cue times to final equivalent tracks.

Checks:

- cue time covered within tolerance
- hotcue slot preserved when policy requires it
- memory cue preserved
- loop start/end preserved
- absent cue reported

### Hotcue Conflict Classification

Classify conflicts before applying any policy:

- already preserved
- preserved at same time but different slot/memory
- safe empty slot add
- memory/non-hotcue absent
- hotcue slot conflict

Policy options can come later. The first useful step is classification and reporting.

## Later Write-Capable Features

These are explicitly out of scope until the verifier and planner are reliable.

### Safe File Operations

Possible future operations:

- copy files
- move files
- rename superseded files
- quarantine files
- convert formats through `ffmpeg`

Required safety:

- dry-run default
- manifest required
- no delete-first behavior
- checksum before and after
- rollback instructions
- post-apply audit

### Rekordbox XML Writer

Possible future operations:

- create importable playlist XML
- rewrite playlist references
- generate cue XML
- validate XML shape against golden fixtures

### Rekordbox DB Writer

This is the highest-risk feature and should come late.

Required safety:

- Rekordbox closed check
- WAL/SHM sidecar check
- timestamped backup
- staged DB copy
- schema fingerprint
- hash verification after install
- query verification after install
- apply audit
- final XML proof export

## Agent And Packaging Features

### Codex Skill

Provide a repo skill that teaches Codex how to use `djlib-doctor` safely.

### Codex Plugin

Package the skill and metadata so Codex users can install it.

### Claude Desktop Extension

Package the stable CLI workflow for Claude Desktop users. This is allowed as an install surface, but the near-term project should not build a standalone MCP server product.

### Public Discoverability

Prepare:

- GitHub topics
- PyPI metadata
- `llms.txt`
- example prompts
- demo reports
- fixture gallery
