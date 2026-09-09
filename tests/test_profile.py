import json, unittest
from pathlib import Path
from backend.profile import UserProfile, confirm_profile, to_scoring_profile
from backend.scoring import load_json, load_rules, score_opportunities
ROOT=Path(__file__).resolve().parents[1]

class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/"data/profile_edwinayyy_candidate.json").read_text(encoding="utf-8"))
    def test_profile_is_structured(self):
        self.assertEqual(UserProfile.model_validate(self.data).profile_status,"confirmed")
        self.assertEqual(len(self.data["confirmed_fields"]),3)
    def test_partial_confirmation_is_blocked(self):
        with self.assertRaises(ValueError): confirm_profile(self.data,["account_stage"])
    def test_all_inferences_can_be_confirmed(self):
        fields=[x["field"] for x in self.data["candidate_inferences_requiring_confirmation"]]
        self.assertEqual(confirm_profile(self.data,fields)["profile_status"],"confirmed")
    def test_confirmed_profile_enters_scoring(self):
        scoring_profile=to_scoring_profile(self.data)
        market=load_json(ROOT/"mock_data/market.json")["records"]
        trends=load_json(ROOT/"mock_data/trends.json")["records"]
        result=score_opportunities(scoring_profile,market,trends,load_rules())
        self.assertEqual(result["status"],"ok")
        pet=next(x for x in result["opportunities"] if x["listing_name"]=="宠物拟人头像")
        self.assertFalse(pet["eligible"])
        self.assertEqual(pet["components"]["profile_match"],0)
        self.assertIn("product_form_mismatch",pet["blocking_reasons"])
        self.assertIn("medium_missing",pet["blocking_reasons"])
        self.assertIsNone(pet["opportunity_score"])
