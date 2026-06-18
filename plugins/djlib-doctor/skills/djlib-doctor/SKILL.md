---
name: djlib-doctor
description: Verify, plan, stage, and safely migrate Rekordbox and Serato DJ libraries with djlib-doctor.
---

# djlib-doctor

Use this skill when the user wants safe help with Rekordbox XML exports, Serato libraries, cleanup plans, cue preservation, staged installs, or two-way Rekordbox/Serato migration.

## Safety Rules

- Start read-only with `verify`, `snapshot`, `inspect`, `plan`, `compare`, or `port`.
- Do not write to Rekordbox except through `install rekordbox-db`, `install rekordbox-convert`, or `install rekordbox-move` after staging prints an exact install token.
- Do not write to Serato except through `install serato-stage` or `install serato-tags` after staging.
- Do not move, convert, delete, or overwrite music files except through `install file-ops`, `install rekordbox-convert`, or `install rekordbox-move`.
- Treat streaming placeholders as placeholders, not missing local files.
- Preserve cue semantics: memory cues, hotcue slots, cue-vs-loop type, and loop ends.
- Use synthetic fixtures for tests and never modify a user's real library during tests.

## Common Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m djlib_doctor.cli verify export.xml
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
PYTHONPATH=src python3 -m djlib_doctor.cli plan missing-files --snapshot run/snapshot.json --out run/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates.json --collision-policy cue-safe
PYTHONPATH=src python3 -m djlib_doctor.cli fingerprint compare copy-a.wav copy-b.wav --out run/file-compare.json
PYTHONPATH=src python3 -m djlib_doctor.cli fingerprint scan ~/Music --out run/fingerprints.json --redact-paths
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan run/plan-missing-files.json --out run/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline before.xml --final after.xml --out run/compare.json
PYTHONPATH=src python3 -m djlib_doctor.cli inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / Set" --out run/rb-to-serato --verify-preview
PYTHONPATH=src python3 -m djlib_doctor.cli certify rb-to-serato --port-manifest run/rb-to-serato/port-manifest.json --out run/rb-to-serato/certification.json
PYTHONPATH=src python3 -m djlib_doctor.cli stage serato --port-manifest run/rb-to-serato/port-manifest.json --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --stage-dir run/serato-stage
PYTHONPATH=src python3 -m djlib_doctor.cli install serato-stage --stage-dir run/serato-stage --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --confirm-token INSTALL_SERATO_STAGE:...
PYTHONPATH=src python3 -m djlib_doctor.cli port serato-to-rb --serato-library-dir "/path/to/serato-library" --crate "/path/to/_Serato_/Subcrates/My.crate" --collection-root ~/Music --out run/serato-to-rb
PYTHONPATH=src python3 -m djlib_doctor.cli certify serato-to-rb --port-manifest run/serato-to-rb/port-manifest.json --out run/serato-to-rb/certification.json
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-db-import --db /path/to/rekordbox/master.db --port-manifest run/serato-to-rb/port-manifest.json --stage-dir run/rekordbox-stage
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-convert --db /path/to/rekordbox/master.db --operations run/convert.json --stage-dir run/rekordbox-convert --cue-shift auto
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-move --db /path/to/rekordbox/master.db --operations run/move.json --stage-dir run/rekordbox-move
PYTHONPATH=src python3 -m djlib_doctor.cli install rekordbox-db --stage-dir run/rekordbox-stage --db /path/to/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
PYTHONPATH=src python3 -m djlib_doctor.cli install rekordbox-convert --stage-dir run/rekordbox-convert --db /path/to/rekordbox/master.db --confirm-token INSTALL_REKORDBOX_CONVERT:...
PYTHONPATH=src python3 -m djlib_doctor.cli install rekordbox-move --stage-dir run/rekordbox-move --db /path/to/rekordbox/master.db --confirm-token INSTALL_REKORDBOX_MOVE:...
PYTHONPATH=src python3 -m djlib_doctor.cli migrate serato-to-rb --serato-library-dir "/path/to/serato-library" --crate "/path/to/_Serato_/Subcrates/My.crate" --collection-root ~/Music --out run/serato-to-rb --stage-db --rekordbox-db /path/to/rekordbox/master.db
```

## Workflow

1. Choose exactly one scope: one track, one playlist/crate, many playlists, or collection.
2. Choose `--transfer-mode full`, `cues-only`, or `match-only`.
3. Generate and inspect a port manifest before staging.
4. Use fingerprinting for exact duplicate or raw-byte similarity checks, and certify generated port artifacts before install.
5. For staged writes, read the generated manifest and only install with the exact token after the user approves.
6. If a Rekordbox DB schema is unsupported, locked, or not pyrekordbox-readable encrypted, stop and report that the importer failed closed.
7. For Rekordbox AAC/M4A conversion, keep `--cue-shift auto` unless the user has validated that their player honors gapless metadata without stored-position shifts.
