# Claude Guidance For djlib-doctor

`djlib-doctor` helps DJs verify and eventually plan safe cleanup for Rekordbox-oriented music libraries, with read-only/dry-run Serato porting support.

Start with read-only XML verification. Never write to a Rekordbox database, Serato audio tags, move music files, convert audio, quarantine files, or delete anything. Live Serato SQLite/crate install is allowed only through `install serato-stage` after `stage serato` has produced a verified manifest and the caller supplies the exact confirmation token.

Useful commands:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m djlib_doctor.cli verify tests/fixtures/rekordbox/simple.xml --no-file-check
PYTHONPATH=src python3 -m djlib_doctor.cli verify tests/fixtures/rekordbox/simple.xml --no-file-check --json --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml tests/fixtures/rekordbox/simple.xml --out work/snapshot-demo --no-file-check
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml tests/fixtures/rekordbox/simple.xml --out work/snapshot-redacted --no-file-check --redact-paths
PYTHONPATH=src python3 -m djlib_doctor.cli plan missing-files --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-duplicates.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-duplicates-keep-both.json --collision-policy keep-both
PYTHONPATH=src python3 -m djlib_doctor.cli plan bad-paths --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-bad-paths.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --list-profiles
PYTHONPATH=src python3 -m djlib_doctor.cli plan audio-compatibility --probe-csv tests/fixtures/audio/compatibility_probes.csv --out work/snapshot-demo/plan-wav-16.json --profile wav-16
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli decision-sheet --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/decision-sheet.csv
PYTHONPATH=src python3 -m djlib_doctor.cli apply-manifest --plan work/snapshot-demo/plan-missing-files.json --review-log work/snapshot-demo/review-decisions.json --only-reviewed --out work/snapshot-demo/apply-manifest.json
PYTHONPATH=src python3 -m djlib_doctor.cli schema --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline tests/fixtures/rekordbox/simple.xml --final tests/fixtures/rekordbox/simple.xml
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline tests/fixtures/rekordbox/simple.xml --final tests/fixtures/rekordbox/simple.xml --check-files
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --playlist "ROOT / Fixture Playlist" --out work/serato-port-demo --verify-preview
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --playlists-file playlists.txt --summary-only --out work/unused
PYTHONPATH=src python3 -m djlib_doctor.cli stage serato --port-manifest work/serato-port-demo/port-manifest.json --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --stage-dir work/serato-stage
PYTHONPATH=src python3 -m djlib_doctor.cli install serato-stage --stage-dir work/serato-stage --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --confirm-token INSTALL_SERATO_STAGE:...
```

Important concepts:

- Rekordbox collection tracks are under `<COLLECTION><TRACK ...>`.
- Playlist entries are separate `<TRACK Key="...">` references.
- `POSITION_MARK Num="-1"` is a memory cue.
- `POSITION_MARK Num="0"` is hotcue A.
- `POSITION_MARK Type="4"` is a loop.
- Streaming placeholders such as SoundCloud records are not missing local files.

Current project status:

- read-only Rekordbox XML parser exists
- cue parser exists
- verification report exists
- snapshot command exists
- redacted shareable snapshots exist
- read-only missing-files, duplicates, cues, and bad-paths plans exist
- duplicate collision policies and audio compatibility profiles exist
- interactive review and ingestible decision logs exist
- CSV decision-sheet export exists
- dry-run-only apply manifest export exists
- schema discovery exists
- baseline/final export compare exists
- Serato read-only inspection and Rekordbox XML to Serato dry-run port manifests exist
- Serato dry-run planning supports batch playlist files, summary-only reports, cue-count metrics, format capability notes, and crate-preview verification
- Serato stage/install supports SQLite/crate updates with backups, sidecar checks, app-closed checks, exact confirmation tokens, and hash verification
- tests use synthetic fixtures only
- no DB writer exists
