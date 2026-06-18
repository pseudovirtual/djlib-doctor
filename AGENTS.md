# Agent Instructions For djlib-doctor

`djlib-doctor` is a read-only-first DJ library verification and cleanup planning toolkit.

## Current Safety Rules

- Do not write to any Rekordbox database except through `install rekordbox-db` after a staged manifest verifies token, contents, staged hash, source hash, and backups.
- Do not write to any live Serato database except through `install serato-stage` after a staged manifest verifies token, contents, staged hashes, source hash, sidecars, app-closed checks, and backups.
- Do not modify, move, rename, convert, quarantine, or delete real music files except through `install file-ops`, `install rekordbox-convert`, or `install rekordbox-move` after a staged manifest verifies token, contents, hashes, and backups.
- Do not write Serato audio tags except through `install serato-tags` after a staged manifest verifies token, contents, staged hash, source hash, and backups.
- Use synthetic fixtures for tests.
- Follow TDD for user-visible behavior: add or update a focused fixture-backed test before implementation.
- Keep modules DRY and share platform-neutral helpers instead of copying logic between Rekordbox and Serato paths.
- Keep Python and Markdown files under 200 lines where practical; split by responsibility when a file grows.
- Keep collection `<TRACK>` records separate from playlist `<TRACK Key="...">` references.
- Treat streaming placeholders as placeholders, not missing local files.
- Preserve cue semantics: memory cues, hotcue slots, cue vs loop type, loop end times.
- Prefer read-only commands first. Use write-capable commands only when an explicit staged/install workflow exists and the user approves that path.

## Expected Commands

```bash
python3 -m pip install -e ".[dev]"
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m djlib_doctor.cli
PYTHONPATH=src python3 -m djlib_doctor.cli self-test
PYTHONPATH=src python3 -m djlib_doctor.cli detect --json
PYTHONPATH=src python3 -m djlib_doctor.cli doctor
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
PYTHONPATH=src python3 -m djlib_doctor.cli fingerprint compare tests/fixtures/audio/synthetic-a.wav tests/fixtures/audio/synthetic-b.wav --out work/fingerprint-compare.json
PYTHONPATH=src python3 -m djlib_doctor.cli fingerprint scan tests/fixtures --out work/fingerprints.json --redact-paths
PYTHONPATH=src python3 -m djlib_doctor.cli review --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/review-decisions.json
PYTHONPATH=src python3 -m djlib_doctor.cli decision-sheet --plan work/snapshot-demo/plan-missing-files.json --out work/snapshot-demo/decision-sheet.csv
PYTHONPATH=src python3 -m djlib_doctor.cli apply-manifest --plan work/snapshot-demo/plan-missing-files.json --review-log work/snapshot-demo/review-decisions.json --only-reviewed --out work/snapshot-demo/apply-manifest.json
PYTHONPATH=src python3 -m djlib_doctor.cli schema --pretty
PYTHONPATH=src python3 -m djlib_doctor.cli compare exports --baseline tests/fixtures/rekordbox/simple.xml --final tests/fixtures/rekordbox/simple.xml --check-files
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --playlist "ROOT / Fixture Playlist" --out work/serato-port-demo --verify-preview
PYTHONPATH=src python3 -m djlib_doctor.cli certify rb-to-serato --port-manifest work/serato-port-demo/port-manifest.json --out work/serato-port-demo/certification.json
PYTHONPATH=src python3 -m djlib_doctor.cli sync plan --config work/djlib-doctor.json --collection --out work/sync-plan
PYTHONPATH=src python3 -m djlib_doctor.cli sync --config work/djlib-doctor.json --collection --out work/sync-run --apply --yes --skip-process-check
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --playlists-file playlists.txt --summary-only --out work/unused
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --track-id 1 --transfer-mode cues-only --out work/serato-track-demo
PYTHONPATH=src python3 -m djlib_doctor.cli port rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --collection --transfer-mode match-only --out work/serato-collection-demo
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-db-import --db /path/to/rekordbox/master.db --port-manifest work/serato-to-rb/port-manifest.json --stage-dir work/rekordbox-stage
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-db-apply --db /path/to/rekordbox/master.db --apply-manifest work/snapshot-demo/apply-manifest.json --stage-dir work/rekordbox-apply
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-convert --db /path/to/rekordbox/master.db --operations work/rekordbox-convert.json --stage-dir work/rekordbox-convert --cue-shift auto
PYTHONPATH=src python3 -m djlib_doctor.cli stage rekordbox-move --db /path/to/rekordbox/master.db --operations work/rekordbox-move.json --stage-dir work/rekordbox-move
PYTHONPATH=src python3 -m djlib_doctor.cli install rekordbox-move --stage-dir work/rekordbox-move --db /path/to/rekordbox/master.db --confirm-token INSTALL_REKORDBOX_MOVE:...
PYTHONPATH=src python3 -m djlib_doctor.cli stage serato --port-manifest work/serato-port-demo/port-manifest.json --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --stage-dir work/serato-stage
PYTHONPATH=src python3 -m djlib_doctor.cli install serato-stage --stage-dir work/serato-stage --serato-library-dir /path/to/serato-library --serato-music-dir /path/to/_Serato_ --confirm-token INSTALL_SERATO_STAGE:...
PYTHONPATH=src python3 -m djlib_doctor.cli migrate rb-to-serato --rekordbox-xml tests/fixtures/rekordbox/simple.xml --playlist "ROOT / Fixture Playlist" --out work/migrate-demo
```

If bytecode compilation is needed in a sandboxed environment, keep cache writes inside the project:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=work/pycache python3 -m compileall -q src tests
```

## Milestone Focus

The current milestone is safe verification, planning, staged writes, and migration workflows:

- parse Rekordbox XML collection records
- detect local Rekordbox and Serato library paths read-only
- run `doctor` for detection, lightweight verification, and exact next commands
- parse playlist references separately
- parse `POSITION_MARK` memory cues, hotcues, and loops
- classify local file tracks, streaming placeholders, and unknown locations
- produce human-readable and machine-readable reports
- produce read-only plans for missing files, duplicates, cue coverage, and bad path hygiene
- expose user-selectable duplicate collision policies and audio compatibility profiles
- fingerprint local file bytes for exact duplicates or byte similarity
- run interactive CLI review and record ingestible decisions
- export dry-run-only apply manifests without applying them
- inspect Serato root.sqlite read-only and build dry-run Rekordbox XML to Serato port manifests
- support Serato batch playlist dry-runs, summary-only reports, cue-count metrics, format capability notes, and crate-preview verification
- certify generated migration previews and staged artifacts before install
- plan primary-library syncs in either direction with `sync plan`
- support single-track, playlist/crate, multi-playlist, and whole-collection port scopes
- support `full`, `cues-only`, and `match-only` transfer modes in port manifests
- stage and install Serato SQLite/crate changes only through token-gated manifests with backups, sidecar checks, app-closed checks, and hash verification
- for Serato-to-Rekordbox, do not present XML preview as the final write workflow; the intended target flow is port manifest/XML representation, `stage rekordbox-db-import` into a copied plain-SQLite or pyrekordbox-readable encrypted `master.db`, then `install rekordbox-db`

Do not write live DBs directly. The verifier and port manifest are the foundation; staged DB installs are the only approved DB write path.
