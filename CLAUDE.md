# Claude Guidance For djlib-doctor

`djlib-doctor` is a read-only-first DJ library verification, cleanup planning, staging, and migration toolkit for Rekordbox and Serato.

Start with read-only commands. Writes are allowed only through explicit staged install commands with exact confirmation tokens: `install serato-stage`, `install serato-tags`, `install rekordbox-db`, and `install file-ops`.

## Useful Commands

```bash
python3 -m pip install -e ".[dev]"
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m djlib_doctor.cli
PYTHONPATH=src python3 -m djlib_doctor.cli self-test
PYTHONPATH=src python3 -m djlib_doctor.cli detect --json
PYTHONPATH=src python3 -m djlib_doctor.cli doctor
PYTHONPATH=src python3 -m djlib_doctor.cli verify tests/fixtures/rekordbox/simple.xml --no-file-check
PYTHONPATH=src python3 -m djlib_doctor.cli snapshot --rekordbox-xml tests/fixtures/rekordbox/simple.xml --out work/snapshot-demo --no-file-check
PYTHONPATH=src python3 -m djlib_doctor.cli plan missing-files --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-missing-files.json
PYTHONPATH=src python3 -m djlib_doctor.cli plan duplicates --snapshot work/snapshot-demo/snapshot.json --out work/snapshot-demo/plan-duplicates.json --collision-policy cue-safe
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli schema --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli fingerprint compare copy-a.wav copy-b.wav --out work/file-compare.json
PYTHONPATH=src python3 -m djlib_doctor.cli fingerprint scan /path/to/music --out work/fingerprints.json --redact-paths
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline tests/fixtures/rekordbox/simple.xml --final tests/fixtures/rekordbox/simple.xml --check-files
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --playlist "ROOT / Fixture Playlist" --out work/serato-port-demo --verify-preview
PYTHONPATH=src python3 -m djlib_doctor.cli certify rb-to-serato --port-manifest work/serato-port-demo/port-manifest.json --out work/serato-port-demo/certification.json
PYTHONPATH=src python3 -m djlib_doctor.cli sync plan --config work/djlib-doctor.json --collection --out work/sync-plan
PYTHONPATH=src python3 -m djlib_doctor.cli sync --config work/djlib-doctor.json --collection --out work/sync-run --apply --yes --skip-process-check
PYTHONPATH=src python3 -m djlib_doctor.cli stage serato --port-manifest work/serato-port-demo/port-manifest.json --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --stage-dir work/serato-stage
PYTHONPATH=src python3 -m djlib_doctor.cli install serato-stage --stage-dir work/serato-stage --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --confirm-token INSTALL_SERATO_STAGE:...
PYTHONPATH=src python3 -m djlib_doctor.cli port serato-to-rb --serato-library-dir /path/to/serato-library --crate /path/to/_Serato_/Subcrates/My.crate --collection-root ~/Music --out work/serato-to-rb
PYTHONPATH=src python3 -m djlib_doctor.cli certify serato-to-rb --port-manifest work/serato-to-rb/port-manifest.json --out work/serato-to-rb/certification.json
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-db-import --db /path/to/rekordbox/master.db --port-manifest work/serato-to-rb/port-manifest.json --stage-dir work/rekordbox-stage
PYTHONPATH=src python3 -m djlib_doctor.cli install rekordbox-db --stage-dir work/rekordbox-stage --db /path/to/rekordbox/master.db --confirm-token INSTALL_SQLITE_STAGE:...
PYTHONPATH=src python3 -m djlib_doctor.cli migrate serato-to-rb --serato-library-dir /path/to/serato-library --crate /path/to/_Serato_/Subcrates/My.crate --collection-root ~/Music --out work/serato-to-rb --stage-db --rekordbox-db /path/to/rekordbox/master.db
```

## Important Concepts

- Rekordbox collection tracks are separate from playlist `<TRACK Key="...">` references.
- `POSITION_MARK Num="-1"` is a memory cue; `Num="0"` is hotcue A; `Type="4"` is a loop.
- Streaming placeholders are not missing local files.
- Porting commands create manifests first; install commands apply only staged, token-verified artifacts.
- Fingerprinting commands are read-only byte-level helpers; they do not claim acoustic identity.
- Certification commands are read-only scorecards for migration artifacts.
- Serato-to-Rekordbox DB import writes only through staged `master.db` installs. It supports tested plain-SQLite schemas and pyrekordbox-readable encrypted DB fixtures; unsupported or locked DBs fail closed.
