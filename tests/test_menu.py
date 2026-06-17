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

    def test_menu_sync_option_calls_sync_plan_with_prompted_paths(self):
        calls = []
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = handle_menu(
                lambda argv: calls.append(argv) or 0,
                input_func=_Input(["sync", "library.json", "sync-preview"]),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            calls,
            [
                [
                    "sync",
                    "plan",
                    "--config",
                    "library.json",
                    "--collection",
                    "--out",
                    "sync-preview",
                ]
            ],
        )

    def test_menu_config_option_calls_config_init_with_prompted_output(self):
        calls = []
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = handle_menu(
                lambda argv: calls.append(argv) or 0,
                input_func=_Input(["config", "library.json"]),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [["config", "init", "--out", "library.json"]])

    def test_menu_fix_option_runs_plan_then_review(self):
        calls = []
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = handle_menu(
                lambda argv: calls.append(argv) or 0,
                input_func=_Input(["fix", "snapshot.json", "missing.json", "decisions.json"]),
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            calls,
            [
                ["plan", "missing-files", "--snapshot", "snapshot.json", "--out", "missing.json"],
                ["review", "--plan", "missing.json", "--out", "decisions.json"],
            ],
        )


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
