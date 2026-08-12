import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_pipeline.py"
FIXTURE = ROOT / "tests" / "fixtures" / "pipeline.json"

spec = importlib.util.spec_from_file_location("analyze_pipeline", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class RecruitingPipelineTest(unittest.TestCase):
    def setUp(self):
        with FIXTURE.open(encoding="utf-8") as handle:
            self.records = json.load(handle)
        self.report = module.analyze(self.records, as_of=module.parse_time("2026-08-12"))

    def test_stage_counts_and_statuses(self):
        counts = {item["stage"]: item["count"] for item in self.report["stage_counts"]}
        self.assertEqual(counts["interview"], 1)
        self.assertEqual(counts["accepted"], 1)
        self.assertEqual(counts["screen"], 1)
        self.assertEqual(self.report["additional_statuses"][0]["stage"], "rejected")

    def test_transitions_and_fill_time(self):
        transitions = {(item["from_stage"], item["to_stage"]): item["count"] for item in self.report["transitions"]}
        self.assertEqual(transitions[("sourced", "screen")], 2)
        self.assertEqual(transitions[("offer", "accepted")], 1)
        self.assertEqual(self.report["fill_time_days"]["sample_size"], 1)
        self.assertEqual(self.report["fill_time_days"]["median_days"], 15.0)

    def test_source_effectiveness_and_redaction(self):
        sources = {item["source"]: item for item in self.report["source_effectiveness"]}
        self.assertEqual(sources["Referral"]["candidate_count"], 2)
        self.assertEqual(sources["Referral"]["accepted_count"], 1)
        self.assertEqual(sources["Referral"]["accepted_rate"], 0.5)
        self.assertNotIn("c-001", json.dumps(self.report, ensure_ascii=False))

    def test_quality_report_is_explicit(self):
        quality = self.report["quality"]
        self.assertEqual(quality["invalid_dates"], 0)
        self.assertEqual(quality["duplicate_candidate_ids"], 0)
        self.assertIn("fields_present", self.report["scope"])


if __name__ == "__main__":
    unittest.main()
