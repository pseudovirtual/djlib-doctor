# Agent Instructions For djlib-doctor

`djlib-doctor` is a read-only-first DJ library verification and cleanup planning toolkit.

## Current Safety Rules

- Do not write to any Rekordbox database.
- Do not write to any live Serato database.
- Do not modify, move, rename, convert, quarantine, or delete real music files.
- Use synthetic fixtures for tests.
- Keep collection `<TRACK>` records separate from playlist `<TRACK Key="...">` references.
- Treat streaming placeholders as placeholders, not missing local files.
- Preserve cue semantics: memory cues, hotcue slots, cue vs loop type, loop end times.
- Prefer read-only commands and reports until a future milestone defines dry-run manifests and approval boundaries.

## Expected Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m djlib_doctor.cli verify tests/fixtures/rekordbox/simple.xml --no-file-check
PYTHONPATH=src python3 -m djlib_doctor.cli verify --schema-version
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml tests/fixtures/rekordbox/simple.xml --out work/snapshot-demo --no-file-check
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml tests/fixtures/rekordbox/simple.xml --out work/snapshot-redacted --no-file-check --redact-paths
PYTHONPATH=src python3 -m djlib_doctor.cli plan missing-files --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-duplicates.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-duplicates-quality.json --collision-policy quality
PYTHONPATH=src python3 -m djlib_doctor.cli plan bad-paths --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-bad-paths.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --list-profiles
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --probe-csv tests/fixtures/audio/compatibility_probes.csv --out work/snapshot-demo/plan-audio-compatibility.json --profile rekordbox-conservative
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli decision-sheet --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/decision-sheet.csv
PYTHONPATH=src python3 -m djlib_doctor.cli apply-manifest --plan work/snapshot-demo/plan-missing-files.json --review-log work/snapshot-demo/review-decisions.json --only-reviewed --out work/snapshot-demo/apply-manifest.json
PYTHONPATH=src python3 -m djlib_doctor.cli schema --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline tests/fixtures/rekordbox/simple.xml --final tests/fixtures/rekordbox/simple.xml --check-files
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --playlist "ROOT / Fixture Playlist" --out work/serato-port-demo
```

If bytecode compilation is needed in a sandboxed environment, keep cache writes inside the project:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=work/pycache python3 -m compileall -q src tests
```

## Milestone Focus

The current milestone is read-only verification, snapshots, comparisons, and cleanup plans:

- parse Rekordbox XML collection records
- parse playlist references separately
- parse `POSITION_MARK` memory cues, hotcues, and loops
- classify local file tracks, streaming placeholders, and unknown locations
- produce human-readable and machine-readable reports
- produce read-only plans for missing files, duplicates, cue coverage, and bad path hygiene
- expose user-selectable duplicate collision policies and audio compatibility profiles
- run interactive CLI review and record ingestible decisions
- export dry-run-only apply manifests without applying them
- inspect Serato root.sqlite read-only and build dry-run Rekordbox XML to Serato port manifests

Do not start with DB writes. The verifier is the foundation.
