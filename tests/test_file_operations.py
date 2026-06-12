from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

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


if __name__ == "__main__":
    unittest.main()
