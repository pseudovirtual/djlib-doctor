import unittest
from unittest import mock

from tests.support import rekordbox_encrypted_fixture as encrypted


class EncryptedBackendPolicyTests(unittest.TestCase):
    def test_requires_backend_skips_linux(self):
        calls = []

        @encrypted.requires_rekordbox_backend
        def sample():
            calls.append(True)

        with mock.patch.object(encrypted.sys, "platform", "linux"):
            with self.assertRaises(unittest.SkipTest):
                sample()

        self.assertEqual(calls, [])

    def test_requires_backend_skips_missing_backend(self):
        calls = []

        @encrypted.requires_rekordbox_backend
        def sample():
            calls.append(True)

        with mock.patch.object(encrypted.sys, "platform", "darwin"):
            with mock.patch.object(
                encrypted, "_import_pyrekordbox_backend", side_effect=ImportError("missing backend")
            ):
                with self.assertRaises(unittest.SkipTest):
                    sample()

        self.assertEqual(calls, [])

    def test_requires_backend_runs_when_available(self):
        @encrypted.requires_rekordbox_backend
        def sample(value):
            return value + 1

        with mock.patch.object(encrypted.sys, "platform", "darwin"):
            with mock.patch.object(
                encrypted, "_import_pyrekordbox_backend", return_value=(object(), object(), object())
            ):
                result = sample(2)

        self.assertEqual(result, 3)


if __name__ == "__main__":
    unittest.main()
