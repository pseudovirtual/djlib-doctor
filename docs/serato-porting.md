# Serato Porting

`djlib-doctor` keeps the private porting lab separate and only keeps generalized, fixture-tested behavior here.

## Rekordbox To Serato

```bash
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Set" --out run/port --verify-preview
djlib-doctor migrate rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Set" --out run/migrate
```

The dry-run plan writes:

- `port-manifest.json`
- one or more preview `.crate` files
- an unsupported-track CSV

Cue policy:

- hotcue slots 1-8 are preserved when possible
- memory cues are promoted to unused Serato hotcue slots
- loops become saved-loop intents
- hotcue loops also keep hotcue intent

## Serato To Rekordbox

```bash
djlib-doctor port serato-to-rb --serato-library-dir Library --crate Set.crate --collection-root ~/Music --out run/rb
djlib-doctor migrate serato-to-rb --serato-library-dir Library --crate Set.crate --collection-root ~/Music --out run/rb
```

This is preview-only: it writes a manifest and Rekordbox XML preview, not a live Rekordbox DB.

## Staged Serato Install

```bash
djlib-doctor stage serato --port-manifest run/port/port-manifest.json --serato-library-dir Library --serato-music-dir _Serato_ --stage-dir run/stage
djlib-doctor install serato-stage --stage-dir run/stage --serato-library-dir Library --serato-music-dir _Serato_ --confirm-token INSTALL_SERATO_STAGE:...
```

Install refuses when:

- the token is wrong or no longer matches manifest contents
- staged hashes fail
- live `root.sqlite` changed after staging
- Serato sidecars exist
- Serato appears to be running

Backups and install reports are written inside the stage directory.
