---
name: djlib-doctor
description: Verify and plan safe cleanup for Rekordbox and Serato DJ libraries using djlib-doctor; use for Rekordbox XML exports, Serato inspection, Rekordbox-to-Serato dry-run porting, missing files, streaming placeholders, hotcues, memory cues, playlist references, snapshots, missing-file plans, duplicate plans, collision policies, bad-path plans, audio compatibility profiles, and baseline/final export comparisons.
---

# djlib-doctor

Use this skill when the user wants to inspect, verify, snapshot, compare, port, or plan safe cleanup for a Rekordbox-oriented or Serato-adjacent DJ library.

## Safety Rules

- Start read-only.
- Do not write to a Rekordbox database except through `install rekordbox-db` after a verified staged SQLite manifest and exact confirmation token.
- Do not write to a live Serato database except through `install serato-stage` after a verified stage manifest and exact confirmation token.
- Do not modify, move, rename, convert, quarantine, or delete music files except through `install file-ops` after a staged file-operation manifest and exact confirmation token.
- Do not modify a real Rekordbox XML export.
- Do not write Serato audio tags except through `install serato-tags` after a staged audio-tag manifest and exact confirmation token.
- Use `snapshot`, `plan`, `compare`, and `verify` before discussing any future write workflow.
- Treat cue points as creative work that must be preserved.
- Treat streaming placeholders as placeholders, not missing local files.

## Commands

```bash
PYTHONPATH=src python3 -m djlib_doctor.cli verify export.xml
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml export.xml --music-root ~/Music --out run/
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml export.xml --music-root ~/Music --out shareable-run/ --redact-paths
PYTHONPATH=src python3 -m djlib_doctor.cli plan missing-files --snapshot run/snapshot.json --out run/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot run/snapshot.json --out run/plan-duplicates-quality.json --collision-policy quality
PYTHONPATH=src python3 -m djlib_doctor.cli plan bad-paths --snapshot run/snapshot.json --out run/plan-bad-paths.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --list-profiles
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --probe-csv run/audio-probes.csv --out run/plan-audio-compatibility.json --profile rekordbox-conservative
PYTHONPATH=src python3 -m djlib_doctor.cli explain --plan run/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan run/plan-missing-files.json --out run/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli decision-sheet --plan run/plan-missing-files.json --out run/decision-sheet.csv
PYTHONPATH=src python3 -m djlib_doctor.cli apply-manifest --plan run/plan-missing-files.json --review-log run/review-decisions.json --only-reviewed --out run/apply-manifest.json
PYTHONPATH=src python3 -m djlib_doctor.cli schema --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / My Playlist" --out run/rb-to-serato --verify-preview
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml export.xml --playlists-file playlists.txt --summary-only --out run/unused
PYTHONPATH=src python3 -m djlib_doctor.cli stage serato --port-manifest run/rb-to-serato/port-manifest.json --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --stage-dir run/serato-stage
PYTHONPATH=src python3 -m djlib_doctor.cli install serato-stage --stage-dir run/serato-stage --serato-library-dir "/path/to/serato-library" --serato-music-dir "/path/to/_Serato_" --confirm-token INSTALL_SERATO_STAGE:...
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline baseline.xml --final final.xml --out run/compare.json
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline baseline.xml --final final.xml --out run/compare-with-files.json --check-files
```
