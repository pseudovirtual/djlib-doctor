# Serato Golden Fixtures

These fixtures vendor small Markers2 byte vectors for parser tests. They are derived from the documented field layouts in Holzhaus `serato-tags`:

- `docs/fileformats.md`: Serato Markers2 GEOB/storage rules.
- `scripts/serato_markers2.py`: `CueEntry` and `LoopEntry` struct layouts.

The vectors are tiny format fixtures only. They do not contain user library data or audio.

`geob-markers2-real-hotcue.json` is a sanitized real-layout writer fixture for the full GEOB container:
outer `01 01`, wrapped base64 body, decoded `COLOR`/`BPMLOCK`/`CUE` entries, and footer.
