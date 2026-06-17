import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from djlib_doctor.cli import main
from djlib_doctor.file_operations import apply_file_operations_stage, stage_file_operations


class FileOperationsTests(unittest.TestCase):
    def test_stage_and_apply_copy_operation(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source.aiff"
            target = tmp / "target.aiff"
            source.write_bytes(b"audio")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps({"operations": [{"operation": "copy", "source": str(source), "target": str(target)}]}),
                encoding="utf-8",
            )

            stage = stage_file_operations(manifest, tmp / "stage")
            report = apply_file_operations_stage(tmp / "stage", confirm_token=stage.install_token)

            self.assertTrue(report["passed"])
            self.assertEqual(target.read_bytes(), b"audio")

    def test_apply_refuses_wrong_token(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source.aiff"
            target = tmp / "target.aiff"
            source.write_bytes(b"audio")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps({"operations": [{"operation": "copy", "source": str(source), "target": str(target)}]}),
                encoding="utf-8",
            )
            stage_file_operations(manifest, tmp / "stage")

            with self.assertRaises(ValueError):
                apply_file_operations_stage(tmp / "stage", confirm_token="wrong")

    def test_apply_refuses_manifest_changed_after_token_created(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source.aiff"
            target = tmp / "target.aiff"
            source.write_bytes(b"audio")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps({"operations": [{"operation": "copy", "source": str(source), "target": str(target)}]}),
                encoding="utf-8",
            )
            stage = stage_file_operations(manifest, tmp / "stage")
            stage_manifest = tmp / "stage" / "file-operations-stage-manifest.json"
            data = json.loads(stage_manifest.read_text(encoding="utf-8"))
            data["operations"][0]["target"] = str(tmp / "other.aiff")
            stage_manifest.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaises(RuntimeError):
                apply_file_operations_stage(tmp / "stage", confirm_token=stage.install_token)

    def test_move_refuses_when_source_changed_after_stage(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source.aiff"
            target = tmp / "target.aiff"
            source.write_bytes(b"audio")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps({"operations": [{"operation": "move", "source": str(source), "target": str(target)}]}),
                encoding="utf-8",
            )
            stage = stage_file_operations(manifest, tmp / "stage")
            source.write_bytes(b"changed")

            with self.assertRaises(RuntimeError):
                apply_file_operations_stage(tmp / "stage", confirm_token=stage.install_token)

            self.assertEqual(source.read_bytes(), b"changed")

    def test_apply_rolls_back_prior_operations_on_failure(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source1 = tmp / "source1.aiff"
            target1 = tmp / "target1.aiff"
            source2 = tmp / "source2.aiff"
            target2 = tmp / "target2.aiff"
            source1.write_bytes(b"new-one")
            target1.write_bytes(b"old-one")
            source2.write_bytes(b"two")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps(
                    {
                        "operations": [
                            {"operation": "copy", "source": str(source1), "target": str(target1)},
                            {"operation": "move", "source": str(source2), "target": str(target2)},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            stage = stage_file_operations(manifest, tmp / "stage")
            source2.write_bytes(b"changed")

            with self.assertRaises(RuntimeError):
                apply_file_operations_stage(tmp / "stage", confirm_token=stage.install_token)

            self.assertEqual(target1.read_bytes(), b"old-one")
            self.assertEqual(source2.read_bytes(), b"changed")
            self.assertFalse(target2.exists())

    def test_apply_continue_on_error_keeps_prior_operations_and_reports_failure(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source1 = tmp / "source1.aiff"
            target1 = tmp / "target1.aiff"
            source2 = tmp / "source2.aiff"
            target2 = tmp / "target2.aiff"
            source1.write_bytes(b"new-one")
            source2.write_bytes(b"two")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps(
                    {
                        "operations": [
                            {"operation": "copy", "source": str(source1), "target": str(target1)},
                            {"operation": "move", "source": str(source2), "target": str(target2)},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            stage = stage_file_operations(manifest, tmp / "stage")
            source2.write_bytes(b"changed")

            report = apply_file_operations_stage(
                tmp / "stage", confirm_token=stage.install_token, continue_on_error=True
            )

            self.assertFalse(report["passed"])
            self.assertEqual(target1.read_bytes(), b"new-one")
            self.assertEqual(report["errors"][0]["operation_id"], "OP-0002")

    def test_cli_install_file_ops_accepts_continue_on_error(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source1 = tmp / "source1.aiff"
            target1 = tmp / "target1.aiff"
            source2 = tmp / "source2.aiff"
            target2 = tmp / "target2.aiff"
            source1.write_bytes(b"new-one")
            source2.write_bytes(b"two")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps(
                    {
                        "operations": [
                            {"operation": "copy", "source": str(source1), "target": str(target1)},
                            {"operation": "move", "source": str(source2), "target": str(target2)},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            stage = stage_file_operations(manifest, tmp / "stage")
            source2.write_bytes(b"changed")

            exit_code = main(
                [
                    "install",
                    "file-ops",
                    "--stage-dir",
                    str(tmp / "stage"),
                    "--confirm-token",
                    stage.install_token,
                    "--continue-on-error",
                ]
            )
            report = json.loads((tmp / "stage" / "file-operations-install-report.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertFalse(report["passed"])

    def test_stage_convert_fails_clearly_when_ffmpeg_is_missing(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source.wav"
            target = tmp / "target.aiff"
            source.write_bytes(b"audio")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps({"operations": [{"operation": "convert", "source": str(source), "target": str(target)}]}),
                encoding="utf-8",
            )

            with mock.patch("djlib_doctor.file_operations.shutil.which", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "ffmpeg.*install"):
                    stage_file_operations(manifest, tmp / "stage")

    def test_apply_copy_writes_target_with_atomic_replace(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source.aiff"
            target = tmp / "target.aiff"
            source.write_bytes(b"audio")
            manifest = tmp / "file-ops.json"
            manifest.write_text(
                json.dumps({"operations": [{"operation": "copy", "source": str(source), "target": str(target)}]}),
                encoding="utf-8",
            )
            stage = stage_file_operations(manifest, tmp / "stage")
            real_replace = os.replace
            calls = []

            def record_replace(src, dst):
                calls.append((Path(src), Path(dst)))
                real_replace(src, dst)

            with mock.patch("djlib_doctor.file_operations.os.replace", side_effect=record_replace):
                apply_file_operations_stage(tmp / "stage", confirm_token=stage.install_token)
            target_bytes = target.read_bytes()

        self.assertEqual(target_bytes, b"audio")
        self.assertEqual(calls[0][1], target)
        self.assertNotEqual(calls[0][0], target)


if __name__ == "__main__":
    unittest.main()
