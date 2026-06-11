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
        self.assertIn("compare", schema_names())
        self.assertIn("decision-sheet", schema_names())
        self.assertIn("review-log", schema_names())
        self.assertIn("apply-manifest", schema_names())
        self.assertIn("serato-inspection", schema_names())
        self.assertIn("port-manifest", schema_names())
        self.assertEqual(get_schema("plan")["schema_version"], "1.0")

    def test_schema_cli_prints_all_schemas(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["schema", "--pretty"])

        data = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertIn("schemas", data)
        self.assertIn("audio-probe-csv", data["schemas"])

    def test_schema_cli_prints_named_schema(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["schema", "decision-sheet"])

        data = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["format"], "csv")
        self.assertIn("decision", data["fields"])


if __name__ == "__main__":
    unittest.main()
