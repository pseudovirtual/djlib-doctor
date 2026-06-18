# Roadmap State

## Phase

Primary-library foundation through Phase F complete; Phase-F verification is in progress before Phase G.

## Last Done

V-F1 confirmed encrypted Rekordbox DB tests run after package install with default dependencies. Minimal `PYTHONPATH` runs still skip cleanly, but installed environments fail if `pyrekordbox` or `sqlcipher3` is missing.

Verification run:

```bash
work/ruff-venv/bin/python -m pip install ".[dev]"
work/ruff-venv/bin/python -m unittest tests.test_encrypted_backend_policy tests.test_rekordbox_encrypted_fixture tests.test_rekordbox_db_read tests.test_rekordbox_db_stage tests.test_rekordbox_db_import
```

Result: 16 tests passed, 0 skipped.

## Next

V-F2: verify `sqlcipher3-wheels` can install across Ubuntu, macOS, and Windows on Python 3.9 and 3.13 before starting Phase G.

## Blockers

TestPyPI trusted publisher setup is a maintainer/account action:

1. Sign in to https://test.pypi.org as the owning account for `djlib-doctor`.
2. Go to Account settings -> Publishing -> Add a new pending publisher.
3. Use owner `pseudovirtual`, repository `djlib-doctor`, workflow name `release.yml`, and environment name `testpypi`.
4. Save the pending publisher for project name `djlib-doctor`.
5. In GitHub, ensure the repository has an environment named `testpypi`; no secrets are needed for trusted publishing.
6. Trigger the `Release` workflow with `workflow_dispatch` or push a pre-release tag such as `v0.1.0rc1`.
7. Confirm the `testpypi-smoke` job installs from TestPyPI and runs `djlib-doctor self-test` on Ubuntu, macOS, and Windows.
