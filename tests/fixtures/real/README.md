# Real Fixtures

This directory is reserved for contributor-supplied anonymized real fixtures.

Keep committed contents limited to documentation and ignore rules. Do not commit private library data, real music files, proprietary database dumps, personal paths, or unredacted metadata.

Expected local-only layout:

```text
manifest.json
serato/geob-tags/
serato/database-v2/
serato/crates/
rekordbox/decrypted-master-db/
rekordbox/xml-exports/
```

When `manifest.json` is absent, real-fixture tests must skip cleanly.
