import json, unittest
from copy import deepcopy
from pathlib import Path
from backend.ai_contracts import build_opportunity_evidence, compose_user_result, structured_output_format, validate_ai_output
ROOT = Path(__file__).resolve().parents[1]

class AIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scoring=json.loads((ROOT/"mock_data/scoring_usr001.json").read_text(encoding="utf-8"))
        cls.package=build_opportunity_evidence(scoring,"MKT-003")
        cls.valid={"schema_version":"1.0.0","task":"opportunity_explanation","status":"ready","candidate_id":"MKT-003",
          "summary":"该方向与用户画像较匹配，但仍应小范围验证。",
          "supporting_reasons":[{"text":"画像与候选题材存在匹配。","evidence_ids":["MKT-003"]}],
          "counter_factors":[],"missing_information":[],"next_actions":["先制作一组可复用的展示样例。"],"citations":["MKT-003"]}
    def test_valid(self): self.assertEqual(validate_ai_output(self.valid,self.package)["status"],"ready")
    def test_unknown_field(self):
        x=deepcopy(self.valid); x["invented_score"]=99
        with self.assertRaises(Exception): validate_ai_output(x,self.package)
    def test_candidate_tampering(self):
        x=deepcopy(self.valid); x["candidate_id"]="MKT-999"
        with self.assertRaises(ValueError): validate_ai_output(x,self.package)
    def test_illegal_citation(self):
        x=deepcopy(self.valid); x["citations"]=["FAKE-001"]
        with self.assertRaises(ValueError): validate_ai_output(x,self.package)
    def test_ready_needs_citation(self):
        x=deepcopy(self.valid); x["citations"]=[]; x["supporting_reasons"]=[]
        with self.assertRaises(ValueError): validate_ai_output(x,self.package)
    def test_digits_blocked(self):
        x=deepcopy(self.valid); x["summary"]="建议先做2个样例。"
        with self.assertRaises(ValueError): validate_ai_output(x,self.package)
    def test_locked_facts_server_owned(self):
        result=compose_user_result(validate_ai_output(self.valid,self.package),self.package)
        self.assertEqual(result["locked_facts"]["opportunity_score"],79.29)
        self.assertNotIn("locked_facts",result["ai_content"])
    def test_strict_format(self): self.assertTrue(structured_output_format("opportunity_explanation")["strict"])
