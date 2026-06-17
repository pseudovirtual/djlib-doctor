import contextlib
import io
import unittest
from unittest import mock

from djlib_doctor.cli import main
from djlib_doctor.cli_menu import handle_menu


class MenuTests(unittest.TestCase):
    def test_bare_cli_menu_can_quit(self):
        stdout = io.StringIO()
        stdin = _InteractiveInput("q\n")

        with mock.patch("sys.stdin", stdin), contextlib.redirect_stdout(stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("djlib-doctor", stdout.getvalue())
        self.assertIn("doctor", stdout.getvalue())

    def test_bare_cli_refuses_noninteractive_menu(self):
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            exit_code = main([])

        self.assertEqual(exit_code, 3)
        self.assertIn("requires interactive stdin", stderr.getvalue())

    def test_menu_doctor_option_calls_doctor_command(self):
        calls = []
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = handle_menu(lambda argv: calls.append(argv) or 0, input_func=_Input(["doctor"]))

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [["doctor"]])


class _InteractiveInput(io.StringIO):
    def isatty(self):
        return True


class _Input:
    def __init__(self, values):
        self.values = list(values)

    def __call__(self, prompt=""):
        print(prompt, end="")
        return self.values.pop(0)


if __name__ == "__main__":
    unittest.main()
