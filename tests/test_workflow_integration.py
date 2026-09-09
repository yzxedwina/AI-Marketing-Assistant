import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import main
from backend.auth import AuthenticatedUser
from backend.main import UIProfileUpdateRequest
from backend.memory import AnalysisRecordInput, MemoryStore, OutcomeRecordInput


USER_ID = "USR-EDWINA-001"
TEST_USER = AuthenticatedUser(USER_ID, "test-user", "测试用户")


class WorkflowIntegrationTests(unittest.TestCase):
    def test_profile_score_plan_and_outcome_share_one_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory) / "workflow.sqlite3")
            with patch.object(main, "memory_store", store):
                saved = main.put_workflow_profile(
                    USER_ID,
                    UIProfileUpdateRequest(
                        goal="吸引潜在客户",
                        direction="动物主题手绘插画",
                        customers="宠物用户、兽设 OC 客户",
                        topics="宠物、兽设",
                        styles="水彩、平涂",
                        services="动物大头挂件、带场景手绘插图",
                        boundaries="电子插画；写实人像",
                        status="可接单",
                        capacity="12 小时 / 周",
                        existing_businesses=[
                            {
                                "id": "business-test",
                                "name": "动物大头挂件",
                                "priceMin": "65",
                                "priceMax": "100",
                                "weeklyCapacity": "10",
                                "durationRange": "3 天",
                            }
                        ],
                    ),
                    current_user=TEST_USER,
                )
                self.assertEqual(saved["profile"]["business_goals"]["primary_goal"], "吸引潜在客户")

                scored = main.get_opportunity_scores(current_user=TEST_USER)
                self.assertTrue(scored["opportunities"])
                chosen = scored["opportunities"][0]
                self.assertTrue(chosen["score_locked"])

                store.add_analysis(USER_ID, AnalysisRecordInput(
                    analysis_type="opportunity",
                    result_id=f"opportunity-{chosen['candidate_id']}",
                    result=chosen,
                ))
                store.add_analysis(USER_ID, AnalysisRecordInput(
                    analysis_type="marketing_plan",
                    result_id=f"plan-{chosen['candidate_id']}-image",
                    result={"candidate": chosen, "content_format": "image_text"},
                ))
                store.add_outcome(USER_ID, OutcomeRecordInput(
                    direction=chosen["name"],
                    platform="xiaohongshu",
                    metrics={"views": 1000, "favorites": 20, "inquiries": 2},
                    capacity_status="available",
                    source="user_reported",
                    observed_at="2026-09-08T00:00:00+00:00",
                ))

                context = main.get_workflow_context(USER_ID, current_user=TEST_USER)
                self.assertIsNotNone(context["memory"]["confirmed_profile"])
                self.assertEqual(len(context["memory"]["analysis_history"]), 2)
                self.assertEqual(len(context["memory"]["outcome_history"]), 1)
                self.assertTrue(context["scoring"]["opportunities"])


if __name__ == "__main__":
    unittest.main()
