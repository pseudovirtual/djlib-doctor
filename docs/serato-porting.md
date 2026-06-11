# Serato Porting

`djlib-doctor` includes read-only and dry-run Serato support for planning Rekordbox-to-Serato workflows.

The separate porting lab remains separate. The open-source project only copies generalized, fixture-tested concepts:

- Serato legacy crate preview generation
- read-only `root.sqlite` inspection
- Rekordbox XML playlist to Serato crate dry-run manifests
- cue intent mapping for hotcues, memory cues, and loops

## Safety Boundary

Current Serato support does not:

- write to a live Serato library
- install staged Serato database files
- modify audio-file metadata tags
- copy, move, convert, or delete music files
- overwrite existing Serato crates

Any future live Serato writer must use staged copies, backups, sidecar checks, integrity checks, review logs, and post-apply verification.

## Inspect Serato

Read a Serato `Library/root.sqlite` schema and row counts:

```bash
djlib-doctor inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato
```

This writes:

- `serato-inspection.json`

The inspection includes table names, columns, row counts, and a schema fingerprint.

## Plan Rekordbox XML To Serato

Create a dry-run port manifest and crate preview from one Rekordbox XML playlist:

```bash
djlib-doctor port rb-to-serato \
  --rekordbox-xml export.xml \
  --playlist "ROOT / My Playlist" \
  --crate-prefix "RB - " \
  --out run/rb-to-serato
```

This writes:

- `port-manifest.json`
- `RB - ... .crate`
- `unsupported.csv`

The `.crate` file is a preview artifact in the output folder. Do not copy it into a live Serato library without a separate reviewed install workflow.

## Cue Policy

Current dry-run cue intent mapping:

- Rekordbox hotcues become Serato hotcue intents in matching slots `1-8`.
- Rekordbox memory cues are promoted into unused Serato hotcue slots.
- Rekordbox loops become Serato saved-loop intents.
- Rekordbox hotcue loops keep both hotcue and saved-loop intent rows.
- Out-of-range cue slots and exhausted Serato slots are reported as unsupported.

The planner does not write Serato audio tags. It records cue intent so future write-capable modules know what would need to be applied and reviewed.
