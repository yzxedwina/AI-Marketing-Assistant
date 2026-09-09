import json
import random
import unittest
from copy import deepcopy
from pathlib import Path

from backend.scoring import build_scoring_result, classify_level, detect_abnormal_growth, load_json, load_rules
from backend.profile import to_scoring_profile


ROOT = Path(__file__).resolve().parents[1]


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = load_rules()
        cls.accounts = load_json(ROOT / "mock_data" / "accounts.json")["records"]
        cls.market = load_json(ROOT / "mock_data" / "market.json")["records"]
        cls.trends = load_json(ROOT / "mock_data" / "trends.json")["records"]

    def canonical(self, value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def test_same_input_produces_identical_output(self):
        first = build_scoring_result(self.accounts[0], self.market, self.trends, self.rules)
        second = build_scoring_result(self.accounts[0], self.market, self.trends, self.rules)
        self.assertEqual(self.canonical(first), self.canonical(second))

    def test_input_order_does_not_change_output(self):
        shuffled_market = deepcopy(self.market)
        shuffled_trends = deepcopy(self.trends)
        random.Random(42).shuffle(shuffled_market)
        random.Random(99).shuffle(shuffled_trends)
        expected = build_scoring_result(self.accounts[0], self.market, self.trends, self.rules)
        actual = build_scoring_result(self.accounts[0], shuffled_market, shuffled_trends, self.rules)
        self.assertEqual(self.canonical(expected), self.canonical(actual))

    def test_unconfirmed_profile_is_blocked(self):
        result = build_scoring_result(self.accounts[-1], self.market, self.trends, self.rules)
        self.assertEqual(result["opportunity_analysis"]["status"], "blocked")
        self.assertEqual(result["opportunity_analysis"]["opportunities"], [])

    def test_single_snapshot_never_claims_growth(self):
        results = detect_abnormal_growth(self.trends, self.rules)
        self.assertTrue(results)
        self.assertTrue(all(row["status"] == "insufficient_history" for row in results))

    def test_growth_detection_with_two_valid_snapshots(self):
        prior = deepcopy(self.trends[0])
        current = deepcopy(self.trends[0])
        prior.update({"like_count": 100, "favorite_count": 50, "comment_count": 20, "interaction_snapshot_at": "2026-08-31T12:00:00+08:00"})
        current.update({"like_count": 3000, "favorite_count": 1200, "comment_count": 300, "interaction_snapshot_at": "2026-09-01T00:00:00+08:00"})
        result = detect_abnormal_growth([current, prior], self.rules)[0]
        self.assertEqual(result["status"], "abnormal_growth")

    def test_threshold_boundaries(self):
        self.assertEqual(classify_level(70, self.rules["hotspot"]["levels"]), "hot")
        self.assertEqual(classify_level(50, self.rules["hotspot"]["levels"]), "watch")
        self.assertEqual(classify_level(49.99, self.rules["hotspot"]["levels"]), "normal")
        self.assertEqual(classify_level(75, self.rules["opportunity"]["levels"]), "recommended")

    def test_outputs_include_audit_fields(self):
        result = build_scoring_result(self.accounts[0], self.market, self.trends, self.rules)
        candidate = result["opportunity_analysis"]["opportunities"][0]
        for key in ("rule_version", "components", "applied_weights", "evidence_ids", "missing_information", "confidence"):
            self.assertIn(key, candidate)

    def test_current_mvp_demo_uses_only_supported_platforms_and_businesses(self):
        demo = load_json(ROOT / "mock_data" / "opportunity_demo.json")
        self.assertTrue(all(row["source_platform"] == "huajia" for row in demo["market"]))
        self.assertNotIn("宠物拟人头像", {row["listing_name"] for row in demo["market"]})
        profile = to_scoring_profile(load_json(ROOT / "data" / "profile_edwinayyy_candidate.json"))
        result = build_scoring_result(profile, demo["market"], demo["trends"], self.rules)
        eligible = [row for row in result["opportunity_analysis"]["opportunities"] if row["eligible"]]
        self.assertEqual(len(eligible), 3)
        self.assertTrue(all(row["opportunity_score"] is not None for row in eligible))
        self.assertTrue(all(row["rule_version"] == self.rules["rule_version"] for row in eligible))
        pendant = next(row for row in eligible if row["listing_name"] == "动物大头手绘挂件")
        self.assertGreaterEqual(pendant["components"]["price_fit"], 60)


if __name__ == "__main__":
    unittest.main()
