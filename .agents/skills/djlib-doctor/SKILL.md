---
name: djlib-doctor
description: Verify and plan safe cleanup for Rekordbox and Serato DJ libraries using djlib-doctor; use for Rekordbox XML exports, Serato inspection, Rekordbox-to-Serato dry-run porting, missing files, streaming placeholders, hotcues, memory cues, playlist references, snapshots, missing-file plans, duplicate plans, collision policies, bad-path plans, audio compatibility profiles, and baseline/final export comparisons.
---

# djlib-doctor

Use this skill when the user wants to inspect, verify, snapshot, compare, port, or plan safe cleanup for a Rekordbox-oriented or Serato-adjacent DJ library.

## Safety Rules

- Start read-only.
- Do not write to a Rekordbox database.
- Do not write to a live Serato database.
- Do not modify, move, rename, convert, quarantine, or delete music files.
- Do not modify a real Rekordbox XML export.
- Do not write Serato audio tags.
- Use `snapshot`, `plan`, `compare`, and `verify` before discussing any future write workflow.
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
PYTHONPATH=src python3 -m djlib_doctor.cli explain --plan run/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan run/plan-missing-files.json --out run/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli decision-sheet --plan run/plan-missing-files.json --out run/decision-sheet.csv
PYTHONPATH=src python3 -m djlib_doctor.cli apply-manifest --plan run/plan-missing-files.json --review-log run/review-decisions.json --only-reviewed --out run/apply-manifest.json
PYTHONPATH=src python3 -m djlib_doctor.cli schema --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli inspect serato --library-dir "/path/to/serato-library" --out run/inspect-serato
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml export.xml --playlist "ROOT / My Playlist" --out run/rb-to-serato
```

Compare baseline/final XML exports:

```bash
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline baseline.xml --final final.xml --out run/compare.json
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline baseline.xml --final final.xml --out run/compare-with-files.json --check-files
```

## Workflow

1. Identify the Rekordbox XML export and optional music root.
2. Run `verify` or `snapshot`.
3. Explain collection tracks, playlist references, local files, streaming placeholders, and cue counts in normal DJ language.
4. If missing files exist, run `plan missing-files`.
5. If duplicate or risky active folder references exist, run `plan duplicates` or `plan bad-paths`.
6. Ask or infer the user's duplicate collision preference and audio compatibility target before choosing `--collision-policy` or `--profile`.
7. Use `review` for row-by-row human decisions; use `decision-sheet` only when a spreadsheet artifact is helpful.
8. If the user has baseline and final XML exports, run `compare exports`.
9. Suggest only read-only next steps unless a future write-capable milestone exists and the user explicitly asks for it.
