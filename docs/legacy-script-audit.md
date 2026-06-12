# Legacy Script Audit

The original private cleanup and Rekordbox-to-Serato experiments informed `djlib-doctor`, but private scripts, private paths, and private music metadata must not be copied into this repo.

## Generalized Use Cases Captured

- verify Rekordbox XML exports before changing anything
- distinguish collection tracks from playlist references
- ignore streaming placeholders as local-file problems
- preserve hotcues, memory cues, loops, and loop end times
- plan missing-file recovery
- choose duplicate survivors with explicit collision policies
- detect bad staging/trash/quarantine path references
- compare before/after exports for lost material or cues
- port Rekordbox playlists to Serato crate previews
- stage Serato DB/crate installs safely
- stage audio tag writes and file operations behind tokens

## Sanitization Rules

- Use synthetic XML, SQLite, crate, and audio fixtures.
- Do not commit real exports, music paths, cue names, crate names, or private DB files.
- Replace personal workflows with generic commands and config keys.
- Keep risky operations behind explicit stage/install commands.

## Remaining Gaps

- More fixture-backed Serato cue/tag parsing.
- More Rekordbox DB fixture coverage before any broader DB write claims.
- Better conversion presets for common DJ software profiles.
