# Roadmap State

## Phase

Code for the current 0.1.0 release target is complete. CI is green on Ubuntu, macOS, and Windows, the TestPyPI publish plus clean-venv `self-test` smoke passed on all three runners, and the remaining work is the maintainer-controlled real PyPI release flow in `docs/RELEASE.md`.

## Last Done

Final 0.1.0 release prep is complete. The README now uses `pip install djlib-doctor` as the primary install path, with source install kept as the development path and the SQLCipher platform caveat kept near install instructions. `pyproject.toml` remains at version `0.1.0` and Development Status `3 - Alpha`. The changelog has a dated 0.1.0 section with validated capabilities, known limitations, TestPyPI smoke success, and final CI hardening. Official GitHub Actions are pinned to Node 24-native majors: `checkout@v7`, `setup-python@v6`, `upload-artifact@v7`, and `download-artifact@v8`.

Windows CI hardening is complete. Rekordbox pyrekordbox reads and writes now close sessions and dispose SQLAlchemy engines through one shared helper before staged replace or temporary-directory cleanup, with tests covering read disposal and a Windows-like `os.replace` refusal when a pyrekordbox handle would remain open. Rekordbox file URL parsing now handles Windows drive URLs, preserves streaming placeholders, and serializes config and Serato-to-Rekordbox manifest paths with forward slashes. Current backend-present macOS gate: `.venv` suite 279 tests green with 3 expected skips, bytecode compile green, Ruff check green, and Ruff format check green. Remote CI is green on Ubuntu, macOS, and Windows for Python 3.9 and 3.13; Linux intentionally skips Rekordbox DB backend tests only.

CI encrypted-DB hardening is complete. Encrypted Rekordbox `master.db` backend tests now use one shared `requires_rekordbox_backend` gate that skips on Linux or unavailable SQLCipher/pyrekordbox backends while leaving platform-agnostic tests running. The encrypted fixture is now built through pyrekordbox's own SQLCipher engine and self-checks by reopening through `read_rekordbox_master_db`; the plain fixture schema has one source, pyrekordbox `Base` over forced `sqlite+pysqlite`, with no hand-maintained fallback schema. `read_rekordbox_master_db` now maps query-time sqlite/sqlcipher/SQLAlchemy driver failures to the clear unsupported/encrypted message, and backup names are hardened so shallow paths cannot escape the stage backup directory. Current backend-present gate: `.venv` suite 273 tests green with 3 expected skips, bytecode compile green, Ruff check green, and Ruff format check green. Current system gate: 273 tests green with 27 expected skips.

CI encrypted-DB fix is complete. `open_master_database` now maps sqlite/sqlcipher/SQLAlchemy database-driver open failures into the existing clear Rekordbox unsupported/encrypted message, so doctor/import refusal paths do not leak raw driver errors. The plain Rekordbox fixture now uses `sqlite+pysqlite` for pyrekordbox Base schema creation and adds the real cue classification columns when needed, keeping it stdlib-readable even when SQLCipher is installed. Current backend-present gate: `.venv` suite 270 tests green with 3 expected skips. Current system gate: 270 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

Release-prep documentation is complete. README and the release changelog now state the validated real-data facts plainly: encrypted Rekordbox `master.db` reads, real `djmdCue` cue semantics, net encoder-delay cue shifting validated on Rekordbox 7.2.8, Serato Markers2 hotcue write validation in Serato DJ, real Serato crate/database V2/tag reads, and real ANLZ offset parsing. Experimental coverage is scoped to ANLZ beat-shift write round-trips, Serato saved-loop GUI display, and broader version coverage. Current gate: 269 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

C9 doctor cleanup is complete. `doctor` now checks Rekordbox `master.db` files through the shared Rekordbox DB reader first, while keeping the old plain-SQLite fixture schema probe only as a fallback for supported synthetic/plain schemas. Added a focused guard proving configured plain DB checks call the shared reader before the fallback. Current gate: 269 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

C8 scoped cue model deduplication is complete. `PortCueTiming` now owns the shared `start_ms`/`end_ms`/`slot`/`label` serialization used by both Rekordbox-to-Serato cue intents and Serato-to-Rekordbox cue rows, while direction-specific fields such as Serato intent/source fields and Rekordbox kind/type/color remain separate. Current gate: 268 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

C7 schema drift guard is complete. `schemas.py` now declares the model-backed schema names, and `tests/test_schemas.py` builds real runtime model examples to assert their `to_dict()` top-level fields match the registered schema fields, including the single and batch variants of the Rekordbox-to-Serato port manifest. Current gate: 267 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

C6 stale capability labels are fixed. Serato format capabilities now mark shipped AIFF/AIF/M4A/MP4/MP3 tag-writing formats as `supported_for_tag_writes`; remaining future/planned wording is still limited to genuinely unimplemented or safety-scoped areas such as acoustic fingerprinting, FLAC/Ogg/WAV Serato cue metadata, and Serato BeatGrid writes. Current gate: 266 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

C5 Rekordbox-to-Serato module split is complete. The public `port_rekordbox_serato.py` module is now a compatibility facade over focused modules for models, planning, cue mapping, output/CSV/summary, format policy, and verification; source modules are under the 200-line guideline and existing imports continue to work. Current gate: 266 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

C4 Serato audio-tag writer cleanup is complete. AIFF and MP3 now share one ID3 writer path for standard frames plus Serato Markers2 GEOB, while MP4 remains format-specific. The staging/install module is back under the 200-line guideline, and the fake mutagen test scaffold moved to shared test helpers. Current gate: 265 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

C3 atomic replacement consolidation is complete. `stage_installer.backup_and_replace()` now owns live-file backup plus same-filesystem temp-copy and `os.replace` semantics, and Rekordbox convert, Rekordbox move, generic SQLite stage, Serato stage, file ops, and Serato audio-tag installs route live replacements through it. Added a shared failure-path test proving a simulated replace error leaves the original live file intact and the backup present. Current gate: 264 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

C2 safety consolidation is complete. `stage_installer.py` now owns shared staged-install guard helpers for confirmation-token recomputation, staged/live hash verification, SQLite sidecar refusal, app-closed refusal, and required backup creation. Rekordbox convert, Rekordbox move, Rekordbox DB stage/import, generic SQLite stage, Serato stage, file ops, and Serato audio tag install paths now use the shared helpers while preserving existing manifest formats and install reports. Current gate: 263 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

J1 release dependency decision is documented: `pyrekordbox` and `sqlcipher3-wheels` remain core dependencies because Rekordbox DB support is core scope. Prebuilt SQLCipher wheels are supported on the current CI matrix, while Intel/x86_64 macOS on Python 3.13 remains a known `pip install` gap; use Apple Silicon or Python <=3.12 on Intel macOS.

Fixed a real Serato Markers2 writer bug: staged audio-tag writes now serialize GEOB data as Serato does, with an outer version header, wrapped base64 body, decoded `COLOR`/`BPMLOCK` defaults plus cue entries and footer, and null padding. Added a sanitized real-layout GEOB golden fixture and writer coverage across AIFF, MP3, and MP4 branches so the writer can no longer pass by raw self-round-trip alone. Current gate: 256 tests green with 23 expected skips, plus bytecode compile, Ruff check, and Ruff format check.

J4 reran and documented the Phase J fixture-hardening gate. The final local suite is green at 254 tests with 23 skips; the skips are the expected SQLCipher/real-data gates in this sandbox. Copy-only `master.db` persistence coverage now exists for convert, move, and Serato-to-Rekordbox import, and encrypted writer tests include plain-SQLite rejection assertions. `docs/phase-i-results.md` records these results and the installed-backend expectation.

J3 added `docs/testing-fixtures.md` and linked it from the docs index. The guide states that fixtures must mirror real bytes, columns, encryption, and tag structure; records database V2, `djmdCue`, ANLZ, and Serato tag mappings; and names `DJLIB_DOCTOR_REAL_*` real-data gates plus the copy-only `master.db` persistence rule.

J2 aligned format fixtures with real structures: Serato `database V2` tests now use `pfil` plus `t*` metadata tags by default, Rekordbox import and encrypted fixtures use real `djmdCue` fields (`OutMsec=-1`, `Kind=slot+1`, `is_hot_cue`/`is_memory_cue`) instead of `HotCue`, and ANLZ helpers document local empty cue containers versus cue-bearing device exports.

J1 made encrypted Rekordbox fixtures the default for convert, move, Rekordbox DB-stage, import, and read writer coverage. Convert, move, and Serato-to-Rekordbox import tests now follow the copy-only persistence pattern: stage/write, copy only `master.db`, reopen the copy, and assert the changed library state. Release CI now installs the package before running tests so installed-backend expectations match the local gate.

Critical J0 follow-up: encrypted Rekordbox writes now force SQLCipher WAL pages into the main `master.db` with `PRAGMA wal_checkpoint(TRUNCATE)` after the write transaction, dispose the writer engine, and refuse zero-row cue/location updates instead of reporting a silent no-op. The canonical encrypted-write test copies only `master.db` after writing and reopens the copy, matching the stage/install copy behavior that exposed the live bug.

J0 routed staged Rekordbox DB operations, conversion, and move/rename DB updates through one encrypted-capable writer. The shared writer uses plain SQLite only for actual plain fixtures and falls back to `open_master_database` when `master.db` is rejected as not plain SQLite, keeping staged hashes, sidecar checks, install tokens, backups, and install verification intact.

Recent Phase I fixes and validation remain recorded: Serato `database V2` nested `otrk` extraction, local ANLZ cue-scope documentation, opt-in local Markers2 validation harness coverage, documented PCOB/PCO2 cue-count offsets, and Rekordbox `djmdCue` real columns/counts.

## Next

Phase J-prep, the J1 SQLCipher matrix decision, and the TestPyPI dry run are complete. Next is human release execution: follow `docs/RELEASE.md`, push `main`, confirm the `pypi` GitHub environment and PyPI trusted publisher, push tag `v0.1.0`, and verify the real PyPI install.

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

PyPI trusted publisher setup and the final release tag are maintainer/account actions. See `docs/RELEASE.md` for the release checklist. Minimum remaining setup:

1. Sign in to https://pypi.org as the owning account for `djlib-doctor`.
2. Go to Account settings -> Publishing -> Add a new pending publisher.
3. Use owner `pseudovirtual`, repository `djlib-doctor`, workflow name `release.yml`, and environment name `pypi`.
4. Save the pending publisher for project name `djlib-doctor`.
5. In GitHub, ensure the repository has an environment named `pypi`; no secrets are needed for trusted publishing.
6. Push `main`, then push tag `v0.1.0`.
7. Confirm the Release workflow publishes to real PyPI and verify `pip install djlib-doctor` plus `djlib-doctor self-test` in a clean venv.
