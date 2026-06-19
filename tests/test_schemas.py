import contextlib
import io
import json
import unittest

from djlib_doctor.apply_manifest import ApplyManifest
from djlib_doctor.certify import CertificationReport
from djlib_doctor.cli import main
from djlib_doctor.compare import CompareReport
from djlib_doctor.fingerprint import FileComparison, FileFingerprint, FingerprintManifest
from djlib_doctor.plan import MatchConfidence, PlanAction, PlanReport
from djlib_doctor.port_rekordbox_serato import RekordboxToSeratoBatchPlan, RekordboxToSeratoPlan
from djlib_doctor.port_serato_rekordbox import SeratoToRekordboxPlan
from djlib_doctor.schemas import MODEL_SCHEMA_NAMES, get_schema, schema_names
from djlib_doctor.serato_sqlite import SeratoInspection, SeratoTableInspection
from djlib_doctor.verify_models import VerificationReport


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

    def test_model_schema_top_level_fields_match_runtime_to_dicts(self):
        cases = _model_schema_cases()

        self.assertEqual(set(cases), set(MODEL_SCHEMA_NAMES))
        for name, examples in cases.items():
            schema_fields = set(get_schema(name)["top_level_fields"])
            runtime_fields = set().union(*(set(example.to_dict()) for example in examples))
            with self.subTest(schema=name):
                self.assertEqual(runtime_fields, schema_fields)


def _model_schema_cases():
    fingerprint = FileFingerprint("track.wav", 4, "0" * 64, (0.0,) * 16)
    action = PlanAction("keep", "1", "Artist", "Title", MatchConfidence.EXACT, False, "reason", ("evidence",))
    return {
        "verification": (VerificationReport("1.0", "export.xml", False, 0, 0, 0, 0, 0, (), 0, 0, 0, 0, ()),),
        "plan": (PlanReport("missing-files", (action,)),),
        "compare": (CompareReport(()),),
        "apply-manifest": (ApplyManifest("missing-files", ({"operation_id": "OP-1"},)),),
        "fingerprint": (fingerprint,),
        "fingerprint-comparison": (FileComparison(fingerprint, fingerprint, 1.0, "exact_duplicate"),),
        "fingerprint-manifest": (FingerprintManifest("root", (fingerprint,)),),
        "certification": (CertificationReport("manifest.json", "rekordbox", "serato", {}, ()),),
        "serato-inspection": (
            SeratoInspection("root.sqlite", (SeratoTableInspection("asset", ("id",), 1),), "0" * 64, {}),
        ),
        "port-manifest": (
            RekordboxToSeratoPlan("Playlist", "RB - Playlist", (), ()),
            RekordboxToSeratoBatchPlan((RekordboxToSeratoPlan("Playlist", "RB - Playlist", (), ()),)),
        ),
        "rekordbox-port-manifest": (SeratoToRekordboxPlan("crate", "Playlist", (), ()),),
    }


if __name__ == "__main__":
    unittest.main()
