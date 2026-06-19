# Roadmap State

## Phase

Primary-library foundation through Phase H is complete. Phase K docs polish is complete. Phase J-prep real-format test hardening is in progress after Phase I validation surfaced false-green fixtures.

## Last Done

Fixed a real Serato Markers2 writer bug: staged audio-tag writes now serialize GEOB data as Serato does, with an outer version header, wrapped base64 body, decoded `COLOR`/`BPMLOCK` defaults plus cue entries and footer, and null padding. Added a sanitized real-layout GEOB golden fixture and writer coverage across AIFF, MP3, and MP4 branches so the writer can no longer pass by raw self-round-trip alone. Current gate: 256 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

J4 reran and documented the Phase J fixture-hardening gate. The final local suite is green at 254 tests with 23 skips; the skips are the expected SQLCipher/real-data gates in this sandbox. Copy-only `master.db` persistence coverage now exists for convert, move, and Serato-to-Rekordbox import, and encrypted writer tests include plain-SQLite rejection assertions. `docs/phase-i-results.md` records these results and the installed-backend expectation.

J3 added `docs/testing-fixtures.md` and linked it from the docs index. The guide states that fixtures must mirror real bytes, columns, encryption, and tag structure; records database V2, `djmdCue`, ANLZ, and Serato tag mappings; and names `DJLIB_DOCTOR_REAL_*` real-data gates plus the copy-only `master.db` persistence rule.

J2 aligned format fixtures with real structures: Serato `database V2` tests now use `pfil` plus `t*` metadata tags by default, Rekordbox import and encrypted fixtures use real `djmdCue` fields (`OutMsec=-1`, `Kind=slot+1`, `is_hot_cue`/`is_memory_cue`) instead of `HotCue`, and ANLZ helpers document local empty cue containers versus cue-bearing device exports.

J1 made encrypted Rekordbox fixtures the default for convert, move, Rekordbox DB-stage, import, and read writer coverage. Convert, move, and Serato-to-Rekordbox import tests now follow the copy-only persistence pattern: stage/write, copy only `master.db`, reopen the copy, and assert the changed library state. Release CI now installs the package before running tests so installed-backend expectations match the local gate.

Critical J0 follow-up: encrypted Rekordbox writes now force SQLCipher WAL pages into the main `master.db` with `PRAGMA wal_checkpoint(TRUNCATE)` after the write transaction, dispose the writer engine, and refuse zero-row cue/location updates instead of reporting a silent no-op. The canonical encrypted-write test copies only `master.db` after writing and reopens the copy, matching the stage/install copy behavior that exposed the live bug.

J0 routed staged Rekordbox DB operations, conversion, and move/rename DB updates through one encrypted-capable writer. The shared writer uses plain SQLite only for actual plain fixtures and falls back to `open_master_database` when `master.db` is rejected as not plain SQLite, keeping staged hashes, sidecar checks, install tokens, backups, and install verification intact.

Recent Phase I fixes and validation remain recorded: Serato `database V2` nested `otrk` extraction, local ANLZ cue-scope documentation, opt-in local Markers2 validation harness coverage, documented PCOB/PCO2 cue-count offsets, and Rekordbox `djmdCue` real columns/counts.

## Next

Phase J-prep is complete. Next is Phase J release work: decide/document the sqlcipher3-wheels coverage gap, then run TestPyPI smoke after maintainer trusted-publisher setup.

Phase I still cannot complete I1, the device-export cue side of I2, or broad I4 golden-vector expansion from synthetic fixtures. Real validation on Rekordbox 7.2.8 and Serato DJ Pro has already confirmed local ANLZ beatgrid parsing, PCOB/PCO2 cue-count offsets for empty local cue containers, Serato crate reading, the Markers2 parser path, and hotcue slot = Kind - 1 for Rekordbox cues. The repo currently has only `tests/fixtures/real/.gitignore` and `tests/fixtures/real/README.md`; there is no `manifest.json` or captured library payload. Provide an approved local-only fixture under `tests/fixtures/real/manifest.json`, following `docs/real-fixtures.md`, with:

- a real encrypted Rekordbox master.db plus safe decrypted copy, app version, and matching redacted XML export for I1
- real `.DAT` and `.EXT` ANLZ files for the same tracks, including PCOB/PCO2 cues, len_cues counts, PQTZ beat times, and PQT2 beat times for I2
- a real Rekordbox import/export check for the target RB version proving whether conversion cue/grid auto shift should be +delay, -delay, or none, including the documented 26ms/gapless behavior for I3
- a real Serato Markers2 and BeatGrid capture from Serato-authored output for I4

After those files are available locally, resume at I1/I2/I4 and add real-fixture tests that skip only when the manifest is absent.

Phase H implementation is complete; Phase I remains the real-world validation checkpoint.

## Phase-F Verification Results

- V-F1: installed encrypted suite ran 16 tests with 0 skips; minimal `PYTHONPATH` runs still skip cleanly, but installed environments fail if `pyrekordbox` or `sqlcipher3` is missing.
- V-F2: `sqlcipher3-wheels` binary wheels resolved for Ubuntu x64, current `macos-latest` arm64, and Windows x64 on Python 3.9 and 3.13. macOS Intel Python 3.13 was checked defensively and did not resolve a wheel, but GitHub's current `macos-latest` runner is arm64.

## Blockers

TestPyPI trusted publisher setup is a maintainer/account action:

1. Sign in to https://test.pypi.org as the owning account for `djlib-doctor`.
2. Go to Account settings -> Publishing -> Add a new pending publisher.
3. Use owner `pseudovirtual`, repository `djlib-doctor`, workflow name `release.yml`, and environment name `testpypi`.
4. Save the pending publisher for project name `djlib-doctor`.
5. In GitHub, ensure the repository has an environment named `testpypi`; no secrets are needed for trusted publishing.
6. Trigger the `Release` workflow with `workflow_dispatch` or push a pre-release tag such as `v0.1.0rc1`.
7. Confirm the `testpypi-smoke` job installs from TestPyPI and runs `djlib-doctor self-test` on Ubuntu, macOS, and Windows.
