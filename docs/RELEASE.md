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

## Dry Run

1. Dispatch the Release workflow manually, or push a prerelease tag such as `v0.1.0rc1`.
2. Confirm the workflow publishes to TestPyPI using the `testpypi` environment.
3. Confirm the clean-venv smoke job installs from TestPyPI and runs `djlib-doctor self-test` on Ubuntu, macOS, and Windows.

## Final Release

1. Only after TestPyPI smoke passes, update the README install path to `pip install djlib-doctor` and commit it.
2. Push the final tag, such as `v0.1.0`.
3. Confirm the Release workflow publishes to real PyPI using the `pypi` environment.
4. Verify `pip install djlib-doctor` from real PyPI in a clean venv.
5. Run `djlib-doctor self-test` in that clean venv.
