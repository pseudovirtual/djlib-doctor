# Phase I Results

## Rekordbox 7.2.8 AAC/M4A Shift

Real-world validation against Rekordbox 7.2.8 confirmed that Rekordbox >=7 ignores AAC gapless metadata for this conversion path. A track converted to AAC/M4A is positioned later than the source in Rekordbox analysis, so the cue/beat shift is positive and `--cue-shift auto` remains the default.

Observed result:

- MP3-to-M4A: the analyzed beatgrid differed by a constant +21 ms across every beat.
- Example first-beat positions: MP3 at 25 ms, M4A at 46 ms.
- WAV-to-M4A: source decoder delay is 0, so the expected shift is the target AAC/M4A skip-samples delay, about ~23 ms.

Precision note: the MP3-to-M4A test measured target M4A skip-samples at about 23 ms, but the real net shift was +21 ms because the source MP3 carried about 2 ms of decoder delay. The correct automatic shift is net delay:

```text
shift_ms = target_decoder_delay_ms - source_decoder_delay_ms
```

Clamp negative results to 0. For lossless WAV/AIFF sources, source delay is 0.
The staged conversion manifest records `source_decoder_delay_ms`, `target_decoder_delay_ms`, and the resulting `cue_shift_ms`.

## Local ANLZ Cue Scope

Real local Rekordbox ANLZ files contain empty cue lists in normal library storage: PCOB/PCO2 container tags are present but have zero PCPT/PCP2 entries. Local user cues live in `master.db` (`djmdCue`), so local convert/in-place flows shift `master.db` cues and ANLZ beatgrids (PQTZ/PQT2) for the library. ANLZ cue-tag shifting applies only to exported device media where Rekordbox writes cue entries into the analysis files.

Validated on 150 real .DAT files and 2160 .EXT files: ANLZ beatgrid parsing and PCOB/PCO2 cue-count offsets had 0 mismatches. Local ANLZ cue lists were empty by design, while beatgrids were present and usable.

## Serato Validation

Real Serato DJ Pro captures confirmed:

- Serato crates: 30/30 real crates parsed, covering 1550 track refs.
- Serato Markers2: real GEOB cue tags parsed through the file-tag path.
- Serato `database V2`: 704/704 real otrk records parsed using database field tags `pfil/tsng/tart/talb/tgen/tkey`.

## Rekordbox djmdCue Validation

Real Rekordbox 7.2.8 `djmdCue` rows confirmed:

- `InMsec` is the cue position in milliseconds.
- `OutMsec=-1` means no loop end; only `OutMsec > 0` is a saved loop.
- `Kind` and `is_hot_cue` classify hotcues; hotcue slot = Kind - 1.
- The validation library read 1086 hotcues, 29 loops, and ~40 memory cues.

## J4 fixture-hardening verification

The Phase J hardening pass reran the full suite at 254 tests. In this local sandbox, SQLCipher-backed tests skip because the backend is not installed; in installed CI/local environments, the encrypted fixture policy fails if the SQLCipher backend is installed incorrectly or missing after package install.

Coverage now includes:

- copy only `master.db` persistence checks for convert, move, and Serato-to-Rekordbox import
- plain-SQLite rejection assertions for encrypted Rekordbox writer fixtures
- real database V2 `pfil/t*` field tags instead of crate-style tags
- real `djmdCue` fields instead of invented `Type` or `HotCue` columns
- local ANLZ empty cue containers plus separate device-export cue fixture coverage
