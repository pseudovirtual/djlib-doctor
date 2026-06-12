# Reports

Reports are the main product surface for `djlib-doctor`.

They should be understandable by DJs and structured enough for agents.

## Human Report Principles

A report should:

- state pass/fail clearly
- explain counts in DJ language
- separate warnings from failures
- avoid panic wording for expected placeholders
- suggest the next safe read-only command

## Current Human Report

Example:

```text
djlib-doctor verification: PASS
Source: export.xml
File existence check: on
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

## JSON Report

Example shape:

```json
{
  "schema_version": "1.0",
  "status": "pass",
  "source": {
    "type": "rekordbox_xml",
    "path": "export.xml",
    "check_files": true
  },
  "counts": {
    "collection_tracks": 3,
    "playlist_references": 2,
    "local_file_tracks": 2,
    "streaming_placeholders": 1,
    "unknown_location_tracks": 0,
    "missing_local_files": 0,
    "cues": 3,
    "hotcues": 2,
    "memory_cues": 1,
    "loops": 1
  },
  "warnings": [],
  "failures": [],
  "next_actions": [
    "Run snapshot when you are ready to inspect the surrounding music folder."
  ]
}
```

## Exit Codes

Exit codes:

- `0`: verification passed
- `1`: verification found failures
- `2`: usage error
- `3`: unreadable or invalid input

## Report Families

The original cleanup required several different report shapes. `djlib-doctor` should name them explicitly.

Schema metadata is available from the CLI:

```bash
djlib-doctor schema --pretty
djlib-doctor schema plan --pretty
djlib-doctor schema review-log --pretty
djlib-doctor schema serato-inspection --pretty
djlib-doctor schema port-manifest --pretty
djlib-doctor schema audio-probe-csv --pretty
```

### Verification Report

Answers:

- what exists now?
- what is missing?
- what is a placeholder?
- what cue data was parsed?

### Candidate Plan

Answers:

- what could be repaired?
- what evidence supports the match?
- what confidence level applies?
- what needs human review?

The first implemented candidate plan is `missing-files`:

```bash
djlib-doctor plan missing-files --snapshot run/snapshot.json --out run/plan-missing-files.json
```

Other current candidate plans:

```bash
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates.json
djlib-doctor plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates-quality.json --collision-policy quality
djlib-doctor plan bad-paths --snapshot run/snapshot.json --out run/plan-bad-paths.json
djlib-doctor plan audio-compatibility --list-profiles
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-audio-compatibility.json
djlib-doctor plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-wav-16.json --profile wav-16
djlib-doctor plan cues --baseline baseline.xml --final final.xml --out run/plan-cues.json
```

The `duplicates` plan supports `cue-safe`, `quality`, and `keep-both` collision policies. Plan actions include the selected policy in metadata so a DJ or agent can explain the recommendation.

The `bad-paths` plan is for active references into staging, temp, quarantine, or other user-defined folder markers. It flags review rows only; it never moves or deletes files.

The `audio-compatibility` plan consumes probe metadata CSV and flags files that fall outside the selected profile. Profiles are recommendations and can be overridden for workflows such as 16-bit AIFF, 24-bit AIFF, WAV-only libraries, or broader software libraries. It does not probe, convert, or rewrite audio files.

### Human Decision Sheet

Answers:

- what choices does the DJ need to make?
- what rows are unsafe for automation?
- what cue conflicts need a policy decision?

Primary interactive command:

```bash
djlib-doctor review --plan run/plan-missing-files.json --out run/review-decisions.json
```

The interactive reviewer walks the plan row by row, prompts for a decision, optionally records notes, and writes `review-decisions.json`. That JSON log is the preferred ingestible review artifact for later modules.

Optional CSV export:

Command:

```bash
djlib-doctor decision-sheet --plan run/plan-missing-files.json --out run/decision-sheet.csv
```

Current CSV sheets include all plan action fields plus blank `decision` and `notes` columns for human review.

### Apply Manifest

Answers:

- what will be changed?
- what source and target paths or records are involved?
- what backups/checksums are required?

Command:

```bash
djlib-doctor apply-manifest --plan run/plan-missing-files.json --review-log run/review-decisions.json --only-reviewed --out run/apply-manifest.json
```

Current apply manifests are dry-run-only. They ingest optional review logs, list proposed operations, required approval, review decisions, and post-apply verification obligations, but they do not apply changes.

### Post-Apply Audit

Answers:

- did the planned action actually happen?
- did verification pass afterward?
- are any cues, playlist entries, or file refs still missing?

JSON and CSV should be available before XLSX. XLSX can be added later because spreadsheet review is useful for large libraries.

### Serato Inspection Report

Answers:

- what tables are present in Serato `root.sqlite`?
- how many rows are in each table?
- what schema fingerprint should later staged writers verify?

Command:

```bash
djlib-doctor inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato
```

### Port Manifest

Answers:

- which Rekordbox XML playlist or playlist batch is being mapped?
- what Serato crate names and preview filenames would be generated?
- which tracks are local and portable?
- what cue/loop intents would need future Serato tag writing?
- which tracks or cues are unsupported?
- how many raw Rekordbox cue rows, unique per-track cues, and Serato-writable cue slots exist?
- which audio extensions are present and what Serato cue-tag capability is known?
- which managed crate namespace is being used?

Command:

```bash
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / My Playlist" --out run/rb-to-serato --verify-preview
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --out run/rb-to-serato-batch
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --summary-only --out run/unused
```

Cue counts deliberately separate source rows from target intents. Rekordbox hotcue-associated loops can map to both a Serato hotcue intent and a saved-loop intent, so the Serato-writable slot count can be larger than the source cue row count.

### Compare Report

Answers:

- is every baseline material track represented in the final export?
- are baseline cue times covered?
- did hotcue counts regress?
- did playlist order or entries change?
- does the final export still reference bad/staging paths?
- does the final export reference missing local files when file checking is requested?

Command:

```bash
djlib-doctor compare exports --baseline baseline.xml --final final.xml --out run/compare.json
djlib-doctor compare exports --baseline baseline.xml --final final.xml --out run/compare-with-files.json --check-files
```

## Snapshot Artifacts

The `snapshot` command currently writes:

- `snapshot.json`: top-level manifest with source paths, artifact paths, verification result, and optional filesystem summary
- `verification.txt`: human-readable verifier output
- `verification.json`: machine-readable verifier output
- `missing-files.csv`: local file-backed collection tracks whose paths are missing
- `streaming-placeholders.csv`: streaming/placeholder collection records
- `cue-summary.csv`: one row per parsed cue
- `playlist-summary.csv`: one row per playlist with entry counts and missing collection refs
- `filesystem-inventory.csv`: audio files under `--music-root`, when provided

When `snapshot --redact-paths` is used, source and music paths are redacted across snapshot artifacts while filenames are preserved. Artifact references inside `snapshot.json` are portable filenames relative to the snapshot directory.
