# Roadmap State

## Phase

Primary-library foundation through Phase F complete; cleanup and bug-fix pass complete. Paused for maintainer review before Phase G.

## Last Done

F3 added pyrekordbox-backed encrypted Rekordbox `master.db` staging/import support through the existing token-gated stage/install flow.

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
