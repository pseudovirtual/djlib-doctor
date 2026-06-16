# Serato Porting

`djlib-doctor` keeps the private porting lab separate and only keeps generalized, fixture-tested behavior here.

## Rekordbox To Serato

```bash
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Set" --out run/port --verify-preview
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --track-id 123 --transfer-mode cues-only --out run/track-cues
djlib-doctor port rb-to-serato --rekordbox-xml export.xml --collection --transfer-mode match-only --out run/collection-match
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
djlib-doctor port serato-to-rb --serato-library-dir Library --portable-id "Music/Track.aiff" --collection-root ~/Music --transfer-mode cues-only --out run/rb-track
djlib-doctor port serato-to-rb --serato-library-dir Library --collection --collection-root ~/Music --out run/rb-collection
djlib-doctor migrate serato-to-rb --serato-library-dir Library --crate Set.crate --collection-root ~/Music --out run/rb
```

This writes a dry-run manifest and Rekordbox XML representation. If the user wants to write to Rekordbox, do not stop at manual XML import. The intended safe path is to stage changes into a copied `master.db`, verify the staged database, then install it with `install rekordbox-db`.

The lower-level staged DB safety path exists:

```bash
djlib-doctor stage rekordbox-db --db /path/to/rekordbox/master.db --operations run/rekordbox-db-operations.json --stage-dir run/rekordbox-stage
djlib-doctor install rekordbox-db --stage-dir run/rekordbox-stage --db /path/to/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
```

The high-level bridge from a Serato-to-Rekordbox port manifest to Rekordbox DB operations is still missing and should be implemented as `stage rekordbox-db-import --port-manifest ...`.

## Scopes And Transfer Modes

Source scopes:

- `--track-id` / `--portable-id`: one track
- `--playlist` / `--crate`: one playlist or crate
- `--playlists-file`: many Rekordbox playlists
- `--collection`: whole available source collection

Transfer modes:

- `full`: tracks plus cue intent where supported by the source adapter
- `cues-only`: cue migration intent for existing matched tracks
- `match-only`: track matching and playlist/crate structure without cue writes

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
