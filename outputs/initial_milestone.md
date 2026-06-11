# djlib-doctor Initial Milestone

## Milestone 1: XML Verifier Alpha

Build the smallest read-only foundation that makes future cleanup safe:

- parse Rekordbox XML collection tracks
- parse playlist references separately from collection tracks
- parse `POSITION_MARK` cues, including memory cues, hotcue slots, and loops
- classify local file-backed tracks, streaming placeholders, and unknown locations
- count missing local files without treating streaming placeholders as missing files
- render a compact verification report
- use only synthetic fixtures in tests

## Why This First

The previous cleanup showed that confusion between raw XML rows, collection records, playlist references, streaming placeholders, and local files caused unnecessary complexity. A verifier that names those categories clearly is the right base layer before matching, planning, file operations, XML writing, or database writing.

## Explicit Non-Goals

- no Rekordbox DB writes
- no file moves, renames, conversions, quarantine, or deletion
- no real music library fixtures
- no automated duplicate matching yet
- no cue merge policy beyond correctly decoding cue semantics
