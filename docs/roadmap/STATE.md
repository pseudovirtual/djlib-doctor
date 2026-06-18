# Roadmap State

## Phase

Primary-library foundation through Phase G is complete. Phase H H2 is implemented and awaiting the H2 commit; Phase I real-library validation is next for cue/grid conversion behavior.

## Last Done

H2 added staged Rekordbox conversion with real ffmpeg encoding, AAC skip-samples compensation, `master.db` cue/path updates, ANLZ PCOB/PCO2 cue shifts, ANLZ PQTZ/PQT2 beatgrid shifts, CI ffmpeg coverage, and `--cue-shift {auto,none}` before token-gated install.

## Next

Phase I validation: use an approved captured Rekordbox library to confirm the correct cue-shift sign/necessity for the target Rekordbox version, including the documented 26ms/gapless behavior, and verify PCOB/PCO2 cue-count offsets plus cue/beat offsets against real `.DAT`/`.EXT` files. H3 remains in the backlog after the conversion validation checkpoint.

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
