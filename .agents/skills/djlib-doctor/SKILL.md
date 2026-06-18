---
name: djlib-doctor
description: Verify and plan safe cleanup for Rekordbox and Serato DJ libraries using djlib-doctor; use for Rekordbox XML exports, Serato inspection, Rekordbox-to-Serato dry-run porting, missing files, streaming placeholders, hotcues, memory cues, playlist references, snapshots, missing-file plans, duplicate plans, collision policies, bad-path plans, audio compatibility profiles, and baseline/final export comparisons.
---

# djlib-doctor

Use this skill when the user wants to inspect, verify, snapshot, compare, port, or plan safe cleanup for a Rekordbox-oriented or Serato-adjacent DJ library.

## Safety Rules

- Start read-only.
- Do not write to a Rekordbox database except through `install rekordbox-db` after a staged SQLite manifest verifies token, contents, staged hash, source hash, and backups.
- Do not write to a live Serato database except through `install serato-stage` after the stage verifies token, contents, staged hashes, source hash, sidecars, app-closed checks, and backups.
- Do not modify, move, rename, convert, quarantine, or delete music files except through `install file-ops` or `install rekordbox-convert` after a staged manifest verifies token, contents, hashes, and backups.
- Do not modify a real Rekordbox XML export.
- Do not write Serato audio tags except through `install serato-tags` after a staged audio-tag manifest verifies token, contents, staged hash, source hash, and backups.
- Use `snapshot`, `plan`, `compare`, `verify`, and `port` before discussing any staged write workflow.
- Treat cue points as creative work that must be preserved.
- Treat streaming placeholders as placeholders, not missing local files.

## Common Commands

Verify an XML export:

```bash
PYTHONPATH=src python3 -m djlib_doctor.cli verify export.xml
```

Create a snapshot:

```bash
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml export.xml --music-root ~/Music --out shareable-run/ --redact-paths
```

Plan missing-file review actions:

```bash
PYTHONPATH=src python3 -m djlib_doctor.cli plan missing-files --snapshot run/snapshot.json --out run/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates-quality.json --collision-policy quality
PYTHONPATH=src python3 -m djlib_doctor.cli plan bad-paths --snapshot run/snapshot.json --out run/plan-bad-paths.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --list-profiles
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-audio-compatibility.json --profile rekordbox-conservative
PYTHONPATH=src python3 -m djlib_doctor.cli fingerprint compare copy-a.wav copy-b.wav --out run/file-compare.json
PYTHONPATH=src python3 -m djlib_doctor.cli fingerprint scan ~/Music --out run/fingerprints.json --redact-paths
PYTHONPATH=src python3 -m djlib_doctor.cli explain --plan run/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan run/plan-missing-files.json --out run/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli decision-sheet --plan run/plan-missing-files.json --out run/decision-sheet.csv
PYTHONPATH=src python3 -m djlib_doctor.cli apply-manifest --plan run/plan-missing-files.json --review-log run/review-decisions.json --only-reviewed --out run/apply-manifest.json
PYTHONPATH=src python3 -m djlib_doctor.cli schema --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli doctor
PYTHONPATH=src python3 -m djlib_doctor.cli
PYTHONPATH=src python3 -m djlib_doctor.cli inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / My Playlist" --out run/rb-to-serato --verify-preview
PYTHONPATH=src python3 -m djlib_doctor.cli certify rb-to-serato --port-manifest run/rb-to-serato/port-manifest.json --out run/rb-to-serato/certification.json
PYTHONPATH=src python3 -m djlib_doctor.cli sync plan --config run/djlib-doctor.json --collection --out run/sync-plan
PYTHONPATH=src python3 -m djlib_doctor.cli sync --config run/djlib-doctor.json --collection --out run/sync-run --apply --yes
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --summary-only --out run/unused
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml export.xml --track-id 123 --transfer-mode cues-only --out run/rb-track-cues
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml export.xml --collection --transfer-mode match-only --out run/rb-collection-match
PYTHONPATH=src python3 -m djlib_doctor.cli port serato-to-rb --serato-library-dir "/path/to/serato-library" --portable-id "Music/Track.aiff" --collection-root ~/Music --transfer-mode cues-only --out run/serato-track-cues
PYTHONPATH=src python3 -m djlib_doctor.cli port serato-to-rb --serato-library-dir "/path/to/serato-library" --collection --collection-root ~/Music --out run/serato-collection
PYTHONPATH=src python3 -m djlib_doctor.cli certify serato-to-rb --port-manifest run/serato-collection/port-manifest.json --out run/serato-collection/certification.json
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-db-import --db /path/to/rekordbox/master.db --port-manifest run/serato-to-rb/port-manifest.json --stage-dir run/rekordbox-stage
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-db-apply --db /path/to/rekordbox/master.db --apply-manifest run/check/apply.json --stage-dir run/rekordbox-apply
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-convert --db /path/to/rekordbox/master.db --operations run/convert.json --stage-dir run/rekordbox-convert --cue-shift auto
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-db --db /path/to/rekordbox/master.db --operations run/rekordbox-db-operations.json --stage-dir run/rekordbox-stage
PYTHONPATH=src python3 -m djlib_doctor.cli install rekordbox-db --stage-dir run/rekordbox-stage --db /path/to/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
PYTHONPATH=src python3 -m djlib_doctor.cli install rekordbox-convert --stage-dir run/rekordbox-convert --db /path/to/rekordbox/master.db --confirm-token INSTALL_REKORDBOX_CONVERT:...
PYTHONPATH=src python3 -m djlib_doctor.cli stage serato --port-manifest run/rb-to-serato/port-manifest.json --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --stage-dir run/serato-stage
PYTHONPATH=src python3 -m djlib_doctor.cli install serato-stage --stage-dir run/serato-stage --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --confirm-token INSTALL_SERATO_STAGE:...
PYTHONPATH=src python3 -m djlib_doctor.cli migrate serato-to-rb --serato-library-dir "/path/to/serato-library" --crate "/path/to/_Serato_/Subcrates/My.crate" --collection-root ~/Music --out run/serato-to-rb --stage-db --rekordbox-db /path/to/rekordbox/master.db
```

Compare baseline/final XML exports:

```bash
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline baseline.xml --final final.xml --out run/compare.json
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline baseline.xml --final final.xml --out run/compare-with-files.json --check-files
```

## Workflow

1. Identify the Rekordbox XML export and optional music root.
2. Run `doctor`, `verify`, or `snapshot`.
3. Explain collection tracks, playlist references, local files, streaming placeholders, and cue counts in normal DJ language.
4. If missing files exist, run `plan missing-files`.
5. If duplicate or risky active folder references exist, run `plan duplicates` or `plan bad-paths`.
6. Ask or infer the user's duplicate collision preference and audio compatibility target before choosing `--collision-policy` or `--profile`.
7. Use `review` for row-by-row human decisions. Enter accepts the recommended choice, `A` accepts remaining high-confidence rows, and `u` undoes the last decision; use `decision-sheet` only when a spreadsheet artifact is helpful.
8. If the user has baseline and final XML exports, run `compare exports`.
9. Use `fingerprint compare` or `fingerprint scan` only for exact duplicate or raw-byte similarity checks; it is not acoustic matching.
10. For porting, choose exactly one source scope: one track, one playlist/crate, many playlists, or a collection.
11. Use `--transfer-mode full`, `--transfer-mode cues-only`, or `--transfer-mode match-only` to make migration intent explicit.
12. Certify generated migration outputs with `certify rb-to-serato` or `certify serato-to-rb` before staging or installing.
13. Use `sync plan` when a config primary should choose the migration direction; it supports both Rekordbox and Serato as primary and remains dry-run-only.
14. Use `sync` as a dry-run by default; add `--apply` only when the user wants the approved stage/install pipeline, then require typed `yes`, `--yes`, or an exact install token.
15. For Rekordbox-to-Serato, prefer `--summary-only` first for batch playlist files, then generate crate previews with `--verify-preview` for single-playlist checks.
16. For Serato-to-Rekordbox, do not stop at “import the XML preview” when the user wants a write workflow. Use `stage rekordbox-db-import` or `migrate serato-to-rb --stage-db`, then `install rekordbox-db`; the DB importer writes only through staged installs and supports tested plain-SQLite schemas plus pyrekordbox-readable encrypted DB fixtures. Unsupported or locked DBs fail closed.
17. For Serato install, require the exact stage token, keep Serato closed, and verify the install report.
18. Suggest only read-only next steps unless a write-capable command already exists with the required safety workflow.
