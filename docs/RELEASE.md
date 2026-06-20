# Release Checklist

Use this checklist for a human-controlled release. Do not publish from a local checkout.

## Before A Release

1. Confirm GitHub environments exist for `testpypi` and `pypi`.
2. Confirm trusted publishers exist on TestPyPI and PyPI:
   - owner: `pseudovirtual`
   - repository: `djlib-doctor`
   - workflow: `release.yml`
   - environment: `testpypi` or `pypi`
3. Re-check the SQLCipher platform caveat: `sqlcipher3-wheels` does not provide every platform/Python wheel. The known gap is Intel/x86_64 macOS on Python 3.13; use Apple Silicon or Python <=3.12 on Intel macOS.

## Completed Dry Run

The 0.1.0 release candidate dry run passed end to end:

1. The Release workflow published to TestPyPI using the `testpypi` environment.
2. GitHub artifact attestations completed.
3. The clean-venv smoke job installed from TestPyPI and ran `djlib-doctor self-test` on Ubuntu, macOS, and Windows.
4. The README primary install path is now `pip install djlib-doctor`.

## Final Release

1. Push `main` after this release-prep commit lands.
2. Confirm the GitHub `pypi` environment exists and the PyPI trusted publisher is configured for owner `pseudovirtual`, repository `djlib-doctor`, workflow `release.yml`, and environment `pypi`.
3. Push the final tag: `v0.1.0`.
4. Confirm the Release workflow publishes to real PyPI using the `pypi` environment.
5. Verify `pip install djlib-doctor` from real PyPI in a clean venv.
6. Run `djlib-doctor self-test` in that clean venv.
