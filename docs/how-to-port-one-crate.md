# Port One Serato Crate To Rekordbox

Use this workflow when you want to move one Serato crate toward Rekordbox without treating the XML preview as the final write step.

## 1. Preview

```bash
djlib-doctor port serato-to-rb --serato-library-dir /path/to/serato-library --crate /path/to/_Serato_/Subcrates/MySet.crate --collection-root ~/Music --out run/serato-to-rb
```

Inspect `run/serato-to-rb/port-manifest.json` and `run/serato-to-rb/rekordbox-preview.xml`.

## 2. Certify

```bash
djlib-doctor certify serato-to-rb --port-manifest run/serato-to-rb/port-manifest.json --out run/serato-to-rb/certification.json
```

Read the certification summary before staging. Confirm the matched/unmatched track counts, cue and loop counts, playlist counts, and unsupported rows.

## 3. Stage And Install

```bash
djlib-doctor stage rekordbox-db-import --db /path/to/rekordbox/master.db --port-manifest run/serato-to-rb/port-manifest.json --stage-dir run/rekordbox-stage
djlib-doctor install rekordbox-db --stage-dir run/rekordbox-stage --db /path/to/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
```

Install only after Rekordbox is closed and the stage manifest looks right. The installer verifies the confirmation token, live DB hash, staged DB hash, sidecars, and backup before replacing `master.db`.
