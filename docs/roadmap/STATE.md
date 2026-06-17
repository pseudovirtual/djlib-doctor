# Roadmap State

## Phase

Primary-library foundation through Phase E complete; cleanup and bug-fix pass complete. Feature completion Phase F is in progress.

## Last Done

F2 added a pyrekordbox-backed encrypted Rekordbox `master.db` reader that maps tracks, cues, playlists, and playlist refs into the existing Rekordbox library model.

## Next

F3: write to encrypted Rekordbox `master.db` through the existing stage/install engine, preserving token/hash/backup/app-closed safety checks.

## Blockers

TestPyPI trusted publisher setup is a maintainer/account action:

1. Sign in to https://test.pypi.org as the owning account for `djlib-doctor`.
2. Go to Account settings -> Publishing -> Add a new pending publisher.
3. Use owner `pseudovirtual`, repository `djlib-doctor`, workflow name `release.yml`, and environment name `testpypi`.
4. Save the pending publisher for project name `djlib-doctor`.
5. In GitHub, ensure the repository has an environment named `testpypi`; no secrets are needed for trusted publishing.
6. Trigger the `Release` workflow with `workflow_dispatch` or push a pre-release tag such as `v0.1.0rc1`.
7. Confirm the `testpypi-smoke` job installs from TestPyPI and runs `djlib-doctor self-test` on Ubuntu, macOS, and Windows.
