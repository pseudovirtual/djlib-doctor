# Roadmap State

## Phase

Primary-library foundation and Phase-F verification are complete. Paused for maintainer review before Phase G.

## Last Done

V-F2 verified `sqlcipher3-wheels` binary wheel resolution for the current CI matrix:

- Ubuntu x64: Python 3.9 and 3.13 wheels resolved.
- macOS `macos-latest` arm64: Python 3.9 and 3.13 wheels resolved.
- Windows x64: Python 3.9 and 3.13 wheels resolved.

V-F1 also confirmed encrypted Rekordbox DB tests run after package install with default dependencies. Minimal `PYTHONPATH` runs still skip cleanly, but installed environments fail if `pyrekordbox` or `sqlcipher3` is missing. The installed encrypted suite ran 16 tests with 0 skips.

Note: macOS Intel Python 3.13 binary resolution was checked defensively and did not resolve a wheel, but GitHub's current `macos-latest` runner is arm64.

## Next

Maintainer review before Phase G: easy one-off ports with detect/config/flag fallback.

## Blockers

TestPyPI trusted publisher setup is a maintainer/account action:

1. Sign in to https://test.pypi.org as the owning account for `djlib-doctor`.
2. Go to Account settings -> Publishing -> Add a new pending publisher.
3. Use owner `pseudovirtual`, repository `djlib-doctor`, workflow name `release.yml`, and environment name `testpypi`.
4. Save the pending publisher for project name `djlib-doctor`.
5. In GitHub, ensure the repository has an environment named `testpypi`; no secrets are needed for trusted publishing.
6. Trigger the `Release` workflow with `workflow_dispatch` or push a pre-release tag such as `v0.1.0rc1`.
7. Confirm the `testpypi-smoke` job installs from TestPyPI and runs `djlib-doctor self-test` on Ubuntu, macOS, and Windows.
