# djlib-doctor 0.1.0

First public release. A safety-first command-line tool for cleaning up your DJ library and moving it between **Rekordbox** and **Serato** while preserving supported hot cue, loop, and playlist metadata.

```bash
pip install djlib-doctor
djlib-doctor detect
```

## Highlights

- **Read-only by default.** Inspect and plan against your library without changing a thing. Every write is split into a `stage` step (prepare + preview) and an `install` step that only runs when you paste back an exact confirmation token.
- **Cue-safe conversion.** Convert WAV/AIFF/MP3 → M4A and keep your cues aligned — the cue shift compensates for AAC encoder delay automatically.
- **Two-way porting.** Move a single track, a playlist/crate, or a whole collection between Rekordbox and Serato, with `full`, `cues-only`, or `match-only` transfer modes.
- **Library cleanup.** Find missing files (without flagging streaming tracks as broken), real duplicates with cue-aware rules, and broken paths; review decisions interactively.
- **Safe moves & renames.** Relocate a track and have Rekordbox follow the file in the same staged install.
- **Shareable reports.** Produce redacted snapshots you can hand off for help without exposing your folder paths.

## Validated against real libraries

- Reads encrypted Rekordbox `master.db` (tracks, playlists, real `djmdCue` hot cues / memory cues / loops) through pyrekordbox + SQLCipher.
- Cue-safe Rekordbox conversion validated on a real Rekordbox 7.2.8 library, including an encrypted write round-trip where the cue persisted.
- Serato Markers2 hot cue writes confirmed loading at the exact position in real Serato DJ.
- Reads real Serato crates, `database V2` records, and Markers2/BeatGrid tags; parses real Rekordbox ANLZ beatgrid and cue containers.

## Known limitations

- ANLZ beat-shift during conversion still needs a real track-with-ANLZ write round-trip.
- Serato saved-loop display isn't yet verified in the Serato GUI (hot cue display is).
- Version coverage beyond Rekordbox 7.2.8 and captured Serato DJ Pro data is experimental.
- **Intel/x86_64 macOS on Python 3.13** is a known SQLCipher wheel gap — use Python ≤3.12 there, or Apple Silicon.

## Quality

- Green CI on Ubuntu, macOS, and Windows across Python 3.9 and 3.13.
- Published to PyPI via OIDC trusted publishing; verified by a clean-venv install + `self-test`.

Full details in the [CHANGELOG](CHANGELOG.md).
