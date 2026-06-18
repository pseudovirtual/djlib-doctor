# Real Fixtures

This directory is reserved for contributor-supplied anonymized real fixtures.

Keep committed contents limited to documentation and ignore rules. Do not commit private library data, real music files, proprietary database dumps, personal paths, or unredacted metadata.

Expected local-only layout:

```text
manifest.json
serato/geob-tags/
serato/audio-tags/
serato/database-v2/
serato/crates/
rekordbox/decrypted-master-db/
rekordbox/xml-exports/
```

When `manifest.json` is absent, real-fixture tests must skip cleanly.

For the opt-in Serato Markers2 harness, either place private audio files under
`tests/fixtures/real/serato/audio-tags/` or set `DJLIB_DOCTOR_REAL_SERATO` to an
`os.pathsep`-separated list of files/directories. These files stay local-only and
must never be committed.
