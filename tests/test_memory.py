import json
import tempfile
import unittest
from pathlib import Path

from backend.memory import AnalysisRecordInput, MemoryStore, OutcomeRecordInput, PreferenceInput


ROOT = Path(__file__).resolve().parents[1]


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "memory.sqlite3"
        self.profile = json.loads((ROOT / "data/profile_edwinayyy_candidate.json").read_text(encoding="utf-8"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_memory_survives_second_store_instance(self):
        first_visit = MemoryStore(self.db_path)
        first_visit.save_confirmed_profile("user-1", self.profile)
        first_visit.save_preference("user-1", PreferenceInput(key="excluded_business", value=["电子插画", "写实人像"]))
        first_visit.add_analysis("user-1", AnalysisRecordInput(
            analysis_type="opportunity", result_id="analysis-1", result={"direction": "动物大头挂件", "score": 81}
        ))

        second_visit = MemoryStore(self.db_path)
        context = second_visit.load_context("user-1")
        self.assertTrue(context["has_memory"])
        self.assertEqual(context["confirmed_profile"]["profile_status"], "confirmed")
        self.assertEqual(context["confirmed_preferences"][0]["value"], ["电子插画", "写实人像"])
        self.assertEqual(context["analysis_history"][0]["result"]["score"], 81)

    def test_unconfirmed_profile_is_rejected(self):
        self.profile["profile_status"] = "pending_user_confirmation"
        with self.assertRaises(ValueError):
            MemoryStore(self.db_path).save_confirmed_profile("user-1", self.profile)

    def test_outcomes_are_append_only_history(self):
        store = MemoryStore(self.db_path)
        record = OutcomeRecordInput(
            direction="动物大头挂件", platform="xiaohongshu",
            metrics={"views": 1200, "inquiries": 3}, capacity_status="available",
            source="user_reported", observed_at="2026-09-07"
        )
        store.add_outcome("user-1", record)
        store.add_outcome("user-1", record)
        self.assertEqual(len(store.load_context("user-1")["outcome_history"]), 2)


if __name__ == "__main__":
    unittest.main()
