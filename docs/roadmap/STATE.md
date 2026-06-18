# Roadmap State

## Phase

Primary-library foundation through Phase H is complete. Phase K docs polish is complete. Phase I is blocked at I1 until approved real captures are provided.

## Last Done

Bootstrap confirmed H2/H2a/H2b/H2c are already committed, including staged Rekordbox conversion, real ffmpeg M4A encoding, measured skip-samples cue/grid compensation, ANLZ PCOB/PCO2 cue shifts, PQTZ/PQT2 beat shifts, CI ffmpeg installation, and `--cue-shift {auto,none}`.

## Next

Phase I cannot proceed from synthetic fixtures. The repo currently has only `tests/fixtures/real/.gitignore` and `tests/fixtures/real/README.md`; there is no `manifest.json` or captured library payload. Provide an approved local-only fixture under `tests/fixtures/real/manifest.json`, following `docs/real-fixtures.md`, with:

- a real encrypted Rekordbox master.db plus safe decrypted copy, app version, and matching redacted XML export for I1
- real `.DAT` and `.EXT` ANLZ files for the same tracks, including PCOB/PCO2 cues, len_cues counts, PQTZ beat times, and PQT2 beat times for I2
- a real Rekordbox import/export check for the target RB version proving whether conversion cue/grid auto shift should be +delay, -delay, or none, including the documented 26ms/gapless behavior for I3
- a real Serato Markers2 and BeatGrid capture from Serato-authored output for I4

After those files are available locally, resume at I1 and add real-fixture tests that skip only when the manifest is absent.

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
