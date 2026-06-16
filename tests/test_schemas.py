import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.schemas import get_schema, schema_names


class SchemaTests(unittest.TestCase):
    def test_schema_registry_includes_core_reports(self):
        self.assertIn("verification", schema_names())
        self.assertIn("snapshot", schema_names())
        self.assertIn("plan", schema_names())
        self.assertIn("config", schema_names())
        self.assertIn("compare", schema_names())
        self.assertIn("decision-sheet", schema_names())
        self.assertIn("review-log", schema_names())
        self.assertIn("apply-manifest", schema_names())
        self.assertIn("serato-inspection", schema_names())
        self.assertIn("port-manifest", schema_names())
        self.assertIn("rekordbox-port-manifest", schema_names())
        self.assertIn("serato-stage-manifest", schema_names())
        self.assertIn("serato-install-report", schema_names())
        self.assertIn("serato-audio-tag-stage-manifest", schema_names())
        self.assertIn("serato-audio-tag-install-report", schema_names())
        self.assertIn("file-operations-stage-manifest", schema_names())
        self.assertIn("file-operations-install-report", schema_names())
        self.assertIn("rekordbox-db-import-operations", schema_names())
        self.assertIn("rekordbox-db-stage-manifest", schema_names())
        self.assertIn("rekordbox-db-install-report", schema_names())
        self.assertEqual(get_schema("plan")["schema_version"], "1.0")

    def test_schema_cli_prints_all_schemas(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["schema", "--pretty"])

        data = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertIn("schemas", data)
        self.assertIn("audio-probe-csv", data["schemas"])
        self.assertIn("fingerprint-manifest", data["schemas"])
        self.assertIn("certification", data["schemas"])

    def test_schema_cli_prints_named_schema(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["schema", "decision-sheet"])

        data = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["format"], "csv")
        self.assertIn("decision", data["fields"])

    def test_port_manifest_schema_documents_batch_fields(self):
        schema = get_schema("port-manifest")

        self.assertIn("crates", schema["top_level_fields"])
        self.assertIn("warnings", schema["top_level_fields"])
        self.assertIn("cue_counts", schema["summary_fields"])


if __name__ == "__main__":
    unittest.main()
