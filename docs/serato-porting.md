# Serato Porting

`djlib-doctor` includes read-only and dry-run Serato support for planning Rekordbox-to-Serato workflows.

The separate porting lab remains separate. The open-source project only copies generalized, fixture-tested concepts:

- Serato legacy crate preview generation
- read-only `root.sqlite` inspection
- Rekordbox XML playlist to Serato crate dry-run manifests
- batch playlist planning from a text file
- cue-count and audio-format summaries
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

The inspection includes table names, columns, row counts, a schema fingerprint, and optional asset identity counts when `asset.portable_id` is present.

## Plan Rekordbox XML To Serato

Create a dry-run port manifest and crate preview from one Rekordbox XML playlist:

```bash
djlib-doctor port rb-to-serato \
  --rekordbox-xml export.xml \
  --playlist "ROOT / My Playlist" \
  --crate-prefix "RB - " \
  --out run/rb-to-serato \
  --verify-preview
```

This writes:

- `port-manifest.json`
- `RB - ... .crate`
- `unsupported.csv`

The `.crate` file is a preview artifact in the output folder. Do not copy it into a live Serato library without a separate reviewed install workflow.

For repeated migrations, put one Rekordbox playlist path per line in a text file:

```text
ROOT / Warmup
ROOT / Peak Time
ROOT / Closing
```

Then run:

```bash
djlib-doctor port rb-to-serato \
  --rekordbox-xml export.xml \
  --playlists-file playlists.txt \
  --crate-prefix "RB - " \
  --out run/rb-to-serato-batch
```

Use `--summary-only` when you want to inspect the dry-run counts without writing output files:

```bash
djlib-doctor port rb-to-serato \
  --rekordbox-xml export.xml \
  --playlists-file playlists.txt \
  --summary-only \
  --out run/unused
```

The summary reports selected crates, local tracks, skipped tracks, audio format counts, cue intent counts, and warnings.

## Serato Library Surfaces

Serato DJ Pro uses more than one library surface:

- SQLite library state under the Serato `Library` directory
- legacy `.crate` files under `_Serato_/Subcrates`
- cue and loop metadata stored in audio-file tags

`djlib-doctor` currently inspects SQLite read-only and writes `.crate` previews only inside the requested output folder. It does not install crates, modify SQLite, or write audio tags.

## Namespace Policy

The default target crate prefix is `RB - `. The manifest records a namespace policy so repeated dry runs can stay clear about which crates would be managed by a future staged writer.

The planner warns when:

- playlist names only match after trimming whitespace
- sanitized crate filenames collide
- tracks are non-local placeholders
- cue slots are out of Serato range or unavailable

## Cue Policy

Current dry-run cue intent mapping:

- Rekordbox hotcues become Serato hotcue intents in matching slots `1-8`.
- Rekordbox memory cues are promoted into unused Serato hotcue slots.
- Rekordbox loops become Serato saved-loop intents.
- Rekordbox hotcue loops keep both hotcue and saved-loop intent rows.
- Out-of-range cue slots and exhausted Serato slots are reported as unsupported.

The planner does not write Serato audio tags. It records cue intent so future write-capable modules know what would need to be applied and reviewed.

Cue counts are reported three ways because Serato and Rekordbox do not map one-to-one:

- raw Rekordbox cue rows
- unique per-track source cues
- Serato-writable cue slots

For example, a Rekordbox hotcue-associated loop may become both a Serato hotcue intent and a saved-loop intent.

## Audio Format Capability Summary

The planner reports known Serato cue-tag capability by extension:

- AIFF/AIF: future Serato Markers2 support via ID3 GEOB
- M4A/MP4: future Serato markersv2 support via MP4 freeform atom
- MP3: likely future ID3 GEOB support
- FLAC/Ogg/WAV: future/uncertain until fixture-backed validation exists

These are planning signals only. The current tool does not write tags.
