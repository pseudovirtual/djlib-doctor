# Legacy Script Audit

This document captures generalized lessons from the private one-off cleanup scripts that were written during the original Rekordbox library repair project.

Do not publish the original scripts as-is. They contain private paths, private assumptions, and actions that were safe only in a specific local context. The value for `djlib-doctor` is the use-case coverage, not the literal code.

## What Was Reviewed

The prior work included roughly 14k lines of project-specific Python plus many CSV, XLSX, and Markdown reports.

Script families reviewed:

- missing-reference analysis and repair planning
- duplicate survivor planning
- clean playlist generation
- cue union and cue preservation checks
- hotcue slot conflict reporting
- latest-wins hotcue conflict application
- original cue repair into a staged database
- audio duplicate scanning
- audio feature similarity verification
- USB/file compatibility probing
- bad path reference cleanup planning
- synchronized file cleanup planning
- folder organization planning
- non-audio artifact cleanup planning
- quarantine manifest generation
- post-repair materiality and playlist order audits
- final unsafe swap verification

## Generalized Use Cases To Capture

### 1. Missing Local File References

User question:

> Which Rekordbox records point at local files that no longer exist?

General behavior:

- parse XML collection tracks
- ignore streaming placeholders
- check local paths
- group missing records by playlist presence
- distinguish "safe to ignore/delete old record" from "playlist still needs this track"
- suggest reacquire/manual match when no safe equivalent exists

Fixture needs:

- missing local path with no playlist refs
- missing local path still referenced by playlist
- missing local path with compatible equivalent
- missing local path with no equivalent
- missing cue-bearing track with no equivalent

### 2. Candidate Matching And Confidence

User question:

> Is this replacement actually the same track?

Evidence tiers observed:

- same path
- exact file hash
- same XML TrackID
- same artist/title
- same normalized filename stem
- close duration
- same audio feature/acoustic signature
- same playlist context
- same source-folder context

General rule:

Filename or title similarity alone is not safe enough for automatic repair. Weak matches should become review rows, not actions.

Fixture needs:

- same track across AIFF/M4A/FLAC
- same title but different remix
- same artist/title with duration mismatch
- filename stem match that should be rejected
- acoustic match that upgrades weak metadata evidence to strong evidence

### 3. Duplicate Survivor Selection

User question:

> Which duplicate record should survive?

Observed policy:

- cue-bearing record usually beats uncued record
- compatible local file beats incompatible or missing file
- playlist-referenced record beats unreferenced duplicate
- better format/quality can win only if cue migration is planned and verified
- `_old`, superseded, backup, or staging filenames should be penalized

Required output:

- duplicate group
- recommended survivor
- role per row: survivor vs remove later
- cue counts
- hotcue counts
- playlist ref counts
- compatibility status
- explanation

Fixture needs:

- duplicate pair where one has cues and one has better file
- duplicate group with multiple cued records and different cue signatures
- duplicate group with no cues and one clear best compatible file
- duplicate group where all candidates are incompatible

### 4. Playlist Consolidation

User question:

> Can duplicate playlists be merged without changing the musical order?

Observed behavior:

- preserve playlist order
- project old TrackIDs through replacement mapping
- dedupe only when policy says duplicate equivalents should collapse
- preserve occurrences when duplicates are intentional
- create clean playlists before deleting old ones
- report omitted tracks and why

Fixture needs:

- duplicate playlist pair
- clean playlist preserving order
- duplicate equivalent collapsed
- duplicate equivalent occurrence preserved
- missing projected playlist entry
- intentionally superseded playlist

### 5. Cue Preservation

User question:

> Did we preserve all cue timing work?

Observed behavior:

- compare original cue times to final equivalent tracks
- allow tolerance for millisecond/frame differences
- preserve loops with start/end
- preserve memory cues
- distinguish same time from same hotcue slot
- report cue-not-covered rows

Fixture needs:

- source cue already present on final track
- source cue present as different slot
- source hotcue demoted to memory cue
- loop start/end preserved
- cue absent from final equivalent

### 6. Hotcue Slot Conflicts

User question:

> What happens when two equivalent tracks both use hotcue A differently?

Observed classification:

- already preserved
- preserved at same time but different slot/memory
- safe empty slot add
- memory/non-hotcue absent
- hotcue slot conflict

Observed policy:

- latest edited cue wins by default
- if latest cue is near-zero and older cue is meaningful, meaningful phrase cue wins
- losing hotcue is demoted to memory cue rather than deleted

Fixture needs:

- empty hotcue slot add
- same slot same time
- same time different slot
- same slot different time conflict
- near-zero latest vs meaningful older phrase point
- losing hotcue demoted to memory cue

### 7. Audio Probe And Compatibility

User question:

> Are these files safe for the target DJ setup?

Observed checks:

- extension
- codec
- sample rate
- bit depth
- duration
- bit rate
- probe success/failure
- known unsupported formats for USB workflows

Important lesson:

Extension is not enough. An `.m4a` might be AAC or ALAC. AIFF/WAV sample rate and bit depth can matter.

Fixture needs:

- AAC-in-M4A
- ALAC-in-M4A
- FLAC
- AIFF 16-bit
- AIFF 24-bit
- high sample-rate WAV/AIFF
- probe failure

### 8. File Organization And Cleanup Planning

User question:

> What files can I safely move, archive, or quarantine?

Observed behavior:

- protect referenced compatible files
- protect unique files with no compatible equivalent
- mark temp staging files
- mark superseded backups
- mark wrong-format duplicates
- require confirmation before cleanup
- generate CSV/XLSX manifests
- produce post-apply audits

Fixture needs:

- referenced compatible file
- referenced incompatible file with compatible equivalent
- unreferenced duplicate
- temp staging file
- superseded backup file
- unique wrong-format file
- non-audio artifact in music folder

### 9. Bad Path Hygiene

User question:

> Are any live Rekordbox references pointing into folders that should not be active?

Observed behavior:

- identify bad path markers
- find clean equivalent or source file
- propose clean target path
- classify clean-copy-needed cases
- report cue-bearing records affected by bad paths

Fixture needs:

- referenced path under bad folder
- matching clean keeper exists
- matching source exists for conversion
- cue-bearing bad-path record
- no clean keeper found

### 10. Database Write Safety

User question:

> If we ever patch the Rekordbox DB, how do we avoid disaster?

Observed guardrails:

- require Rekordbox closed
- check WAL/SHM sidecars
- make timestamped live backup
- copy live DB to stage
- patch staged DB first
- verify staged DB
- install staged DB
- verify live DB afterward
- hash-check or query-check the installed DB
- write apply audit

Current open-source implication:

DB writing must remain a late milestone. The verifier and planner should define the proof obligations before any DB writer exists.

Fixture/test needs:

- WAL/SHM sidecar guard
- process-running guard
- backup creation
- staged patch verification
- failed live install/hash mismatch

### 11. Post-Repair Verification

User question:

> Did the repair actually preserve the library?

Observed audits:

- original material represented in final export
- playlist order projection
- missing projected playlist entries
- bad playlist refs
- bad collection records
- hotcue regressions
- cue coverage
- final missing local files
- final streaming placeholder accounting

Fixture needs:

- baseline/final pair with mapping
- intentionally superseded playlist
- missing projected playlist entry
- hotcue regression
- bad final playlist ref
- all-good final verification

### 12. Human Review Workbooks

User question:

> What decisions do I actually need to make?

Observed report forms:

- summary sheet
- all rows
- needs reacquire
- has replacement
- cue conflict decisions
- cleanup review
- protected referenced files
- post-apply audit

Open-source implication:

CSV and JSON are not enough for all users. Spreadsheet-style reports are valuable for DJs reviewing large libraries, even if they come later than JSON.

## Product Requirements Added From This Audit

The roadmap should include these explicit capabilities:

- report schemas for verification, candidate plans, decision sheets, manifests, and apply audits
- match confidence levels with evidence lists
- fixture families for duplicate/cue/playlist/file-cleanup/audio-probe cases
- compatibility profiles with codec/sample-rate/bit-depth rules
- playlist projection verification
- cue coverage verification
- hotcue slot conflict classification
- human review outputs, eventually including CSV/XLSX
- DB writer proof obligations before DB writer implementation

## What Not To Generalize Yet

Do not generalize:

- private folder names
- hard-coded paths
- one-off playlist names
- one-off TrackID overrides
- live DB patching code
- direct delete scripts
- conversion scripts that write files

Do generalize:

- evidence and confidence model
- safety gates
- report shapes
- fixture categories
- command boundaries
- verification criteria
