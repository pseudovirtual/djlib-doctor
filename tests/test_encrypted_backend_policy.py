import unittest
from unittest import mock

from tests.support import rekordbox_encrypted_fixture as encrypted


class EncryptedBackendPolicyTests(unittest.TestCase):
    def test_installed_package_fails_when_backend_is_missing(self):
        with mock.patch.object(encrypted, "_djlib_doctor_is_installed", return_value=True):
            with self.assertRaises(AssertionError):
                encrypted.skip_or_fail_for_missing_encrypted_backend(self, ImportError("missing backend"))

    def test_minimal_pythonpath_environment_skips_when_backend_is_missing(self):
        with mock.patch.object(encrypted, "_djlib_doctor_is_installed", return_value=False):
            with self.assertRaises(unittest.SkipTest):
                encrypted.skip_or_fail_for_missing_encrypted_backend(self, ImportError("missing backend"))


if __name__ == "__main__":
    unittest.main()
