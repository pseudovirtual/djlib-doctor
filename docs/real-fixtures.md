# Real Fixture Capture

Real fixtures are optional maintainer/contributor inputs for validating behavior against captured DJ-library formats. They are not required for the normal unit suite, and the tests skip cleanly when they are absent.

Do not commit private library data, copyrighted audio, personal paths, playlist names, or proprietary database contents that have not been anonymized and approved for sharing.

## Target Layout

Place approved captured fixtures under `tests/fixtures/real/`:

```text
tests/fixtures/real/
  manifest.json
  serato/
    geob-tags/
    database-v2/
    crates/
  rekordbox/
    decrypted-master-db/
    encrypted-master-db/
    anlz/
    conversion-check/
    xml-exports/
```

The committed directory contains only instructions and ignore rules. Real fixture files should be supplied locally or by a private CI secret/artifact until they are explicitly approved for public use.

## Capture Checklist

Capture a small library with one or two local tracks and simple, named metadata:

- Serato GEOB tags: extract `Serato Markers2` and `Serato BeatGrid` frames from MP3/AIFF/M4A files.
- Serato catalog files: capture `_Serato_/database V2`, `root.sqlite`, and the matching `.crate` files.
- Rekordbox DB: include a local-only encrypted `master.db` plus a safe decrypted master.db copy; modern encrypted SQLCipher databases must not be committed publicly.
- Rekordbox ANLZ: include matching local `.DAT` and `.EXT` files with empty PCOB/PCO2 cue containers plus PQTZ/PQT2 beats; cue-bearing PCOB/PCO2 files should be captured separately from USB/device exports.
- Rekordbox conversion check: record the target Rekordbox version and whether AAC/M4A conversion cues/grids require +delay, -delay, or no stored-position shift.
- Rekordbox XML: export a matching XML export for the same tracks and playlists.
- Audio files: do not commit audio; use hashes and redacted filenames unless the file is freely licensed and approved.

## Required Anonymization

- Replace artist, title, album, comments, and playlist names with neutral fixture names.
- Replace local absolute paths with synthetic paths.
- Remove account identifiers, streaming IDs, purchase IDs, and cloud-sync metadata.
- Keep cue positions, loop ends, hotcue slots, beatgrid markers, colors, ratings, and ordering intact.
- Record the app versions and operating system in `manifest.json`.

## Manifest Shape

```json
{
  "schema_version": "1.0",
  "description": "Small anonymized Serato/Rekordbox fixture bundle",
  "source_versions": {
    "serato": "version or unknown",
    "rekordbox": "version or unknown"
  },
  "fixtures": {
    "serato_geob_tags": [],
    "serato_database_v2": null,
    "serato_crates": [],
    "rekordbox_encrypted_master_db": null,
    "rekordbox_decrypted_master_db": null,
    "rekordbox_anlz_files": [],
    "rekordbox_conversion_check": null,
    "rekordbox_xml_exports": []
  }
}
```

Tests that use this manifest must call `unittest.skipTest(...)` when the manifest or referenced files are absent.

## Generated Rekordbox Fixtures

Encrypted Rekordbox fixture generation is available when the default SQLCipher backend imports successfully. The generator builds a small plain SQLite `master.db` with the target `djmdContent` and `djmdCue` schema, then encrypts a copy using the public Rekordbox 6/7 SQLCipher key and SQLCipher4 settings. If the SQLCipher backend is unavailable, tests skip with a clear message.
