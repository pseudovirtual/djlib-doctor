# Serato Porting

`djlib-doctor` includes read-only, dry-run, staged, and guarded-install Serato support for Rekordbox-to-Serato crate/library workflows.

The separate porting lab remains separate. The open-source project only copies generalized, fixture-tested concepts:

- Serato legacy crate preview generation
- read-only `root.sqlite` inspection
- Rekordbox XML playlist to Serato crate dry-run manifests
- batch playlist planning from a text file
- cue-count and audio-format summaries
- cue intent mapping for hotcues, memory cues, and loops
- staged Serato SQLite and crate updates from a port manifest
- guarded install with backups, hashes, app-closed checks, and an explicit confirmation token

## Safety Boundary

Current Serato support can stage and install Serato SQLite/crate changes, but it still does not:

- modify audio-file metadata tags
- copy, move, convert, or delete music files
- modify Rekordbox databases or XML exports
- write cue data into audio files

The install command is deliberately separate from planning and staging. It refuses to proceed unless the stage verifies, SQLite sidecars are absent, Serato is not running, and the caller supplies the exact install token from the stage manifest.

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

## Stage And Install Serato

The staged workflow consumes a reviewed `port-manifest.json`:

```bash
djlib-doctor stage serato \
  --port-manifest run/rb-to-serato/port-manifest.json \
  --serato-library-dir "/path/to/serato-library" \
  --serato-music-dir "/path/to/_Serato_" \
  --stage-dir run/serato-stage
```

This writes:

- `run/serato-stage/Library/root.sqlite`
- `run/serato-stage/_Serato_/Subcrates/*.crate`
- `run/serato-stage/serato-stage-manifest.json`
- `run/serato-stage/serato-stage-verification.json`

Staging copies the live `root.sqlite` into the stage directory and modifies only that staged copy. It does not write to the live Serato library.

The stage manifest includes an `install_token`. Install requires that token:

```bash
djlib-doctor install serato-stage \
  --stage-dir run/serato-stage \
  --serato-library-dir "/path/to/serato-library" \
  --serato-music-dir "/path/to/_Serato_" \
  --confirm-token "INSTALL_SERATO_STAGE:..."
```

Install behavior:

- refuses if staged hashes fail verification
- refuses if `root.sqlite-wal`, `root.sqlite-shm`, or `root.sqlite-journal` exists
- refuses if Serato appears to be running
- backs up live `root.sqlite` and any overwritten crate files under the stage directory
- installs staged `root.sqlite` and staged crate files
- verifies live installed file hashes against staged files
- writes `serato-install-report.json`

## Serato Library Surfaces

Serato DJ Pro uses more than one library surface:

- SQLite library state under the Serato `Library` directory
- legacy `.crate` files under `_Serato_/Subcrates`
- cue and loop metadata stored in audio-file tags

`djlib-doctor` plans first, stages into a run folder second, and installs only through the explicit `install serato-stage` command. It does not write audio tags.

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
