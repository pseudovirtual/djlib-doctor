# Roadmap State

## Phase

Primary-library foundation through review polish complete; Phase E polish/distribution pass in progress.

## Last Done

E4 added the repo-side TestPyPI trusted-publishing workflow path and cross-OS clean-venv smoke install job.

## Next

Maintainer: configure TestPyPI trusted publishing, then run the Release workflow manually or push a `v0.1.0rc1`-style tag.

## Blockers

TestPyPI trusted publisher setup is a maintainer/account action:

1. Sign in to https://test.pypi.org as the owning account for `djlib-doctor`.
2. Go to Account settings -> Publishing -> Add a new pending publisher.
3. Use owner `pseudovirtual`, repository `djlib-doctor`, workflow name `release.yml`, and environment name `testpypi`.
4. Save the pending publisher for project name `djlib-doctor`.
5. In GitHub, ensure the repository has an environment named `testpypi`; no secrets are needed for trusted publishing.
6. Trigger the `Release` workflow with `workflow_dispatch` or push a pre-release tag such as `v0.1.0rc1`.
7. Confirm the `testpypi-smoke` job installs from TestPyPI and runs `djlib-doctor self-test` on Ubuntu, macOS, and Windows.
