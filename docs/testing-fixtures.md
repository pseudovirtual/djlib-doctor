# Testing Fixtures

Fixture tests are allowed to be synthetic, but DB and format fixtures must mirror real bytes, columns, encryption, and tag structure. A small fake is useful only when it preserves the real contract that production code will see.

## Rules

- Prefer generated encrypted Rekordbox `master.db` fixtures for writer/read happy paths.
- Plain SQLite fixtures are only for explicit unsupported-schema or rejection tests.
- Write tests must prove persistence survives stage/install behavior: write, copy only `master.db`, reopen the copy, and assert the change is present. Do not rely on a live WAL sidecar.
- Format parser fixtures must use confirmed real tags or columns, not adjacent formats.
- Add comments near compact byte fixtures naming the real fields they model.
- Use opt-in private real-data tests as the backstop; never commit private libraries or audio.

## Confirmed Mappings

Serato `database V2` `otrk` records:

- Required metadata tag family: `pfil/tsng/tart/talb/tgen/tkey/tbpm`.
- `pfil` = file path
- `tsng` = title
- `tart` = artist
- `talb` = album
- `tgen` = genre
- `tkey` = key
- `tbpm` = BPM
- Values are UTF-16-BE. `ptrk`/`pnam`/`part` are crate-style fields, not database V2 track metadata.

Rekordbox `djmdCue` rows:

- `InMsec` = cue start in milliseconds
- `OutMsec=-1` or any non-positive value means no loop end; only `OutMsec > 0` is a loop
- `Kind=0` is a memory cue; `Kind>=1` is a hotcue
- hotcue slot = `Kind - 1`
- `is_hot_cue` and `is_memory_cue` are the real classification flags
- Do not invent `Type` or `HotCue` columns in new DB fixtures.

Rekordbox ANLZ:

- local ANLZ files normally contain PCOB/PCO2 containers with zero PCPT/PCP2 cue rows
- local user cues live in `master.db`
- PQTZ and PQT2 beat times are absolute milliseconds and must shift with cue compensation
- cue-bearing PCOB/PCO2 fixtures represent USB/device exports, not the local-library default

Serato audio tags:

- `Serato Markers2` and `Serato BeatGrid` must be validated through the mutagen tag path when real files are configured
- synthetic Markers2 byte fixtures should stay paired with decode/encode/decode golden-vector tests

## Real-Data Backstops

- `DJLIB_DOCTOR_REAL_SERATO` points to private Serato-tagged audio files for opt-in Markers2 validation.
- `DJLIB_DOCTOR_REAL_REKORDBOX_DB` points to a private captured Rekordbox `master.db` for opt-in DB validation.
- `tests/fixtures/real/manifest.json` may reference approved local-only captures following `docs/real-fixtures.md`.

If a fixture cannot model a real format detail without captured data, mark the test skipped behind an explicit real-data gate rather than inventing fields.
