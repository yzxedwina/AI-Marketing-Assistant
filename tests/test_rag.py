import unittest

from backend.rag import answer_question, search_knowledge


class RagTests(unittest.TestCase):
    def test_term_query_retrieves_definition(self):
        result = search_knowledge("约稿里买断是什么意思？")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["evidence"][0]["evidence_id"], "TERM-009")

    def test_medium_distinction(self):
        result = search_knowledge("水彩一定是传统手绘吗？")
        self.assertEqual(result["status"], "ready")
        self.assertIn("TERM-007", result["allowed_evidence_ids"])

    def test_platform_scope_is_visible(self):
        result = search_knowledge("小红书接口可以随便使用客户账号吗？", platform="xiaohongshu")
        self.assertEqual(result["evidence"][0]["knowledge_type"], "platform_rule")
        self.assertIn(result["evidence"][0]["status"], {"active_for_stated_scope", "needs_manual_review"})

    def test_unknown_question_returns_no_answer(self):
        result = search_knowledge("火星插画协会的会员费是多少？", minimum_score=0.35)
        self.assertEqual(result["status"], "no_answer")
        self.assertEqual(result["evidence"], [])

    def test_case_does_not_claim_excellence(self):
        result = search_knowledge("有没有动物挂件案例？", knowledge_types=["reference_case"])
        self.assertEqual(result["status"], "ready")
        self.assertIn("不能", result["evidence"][0]["text"])

    def test_answer_is_cited_and_marks_candidate(self):
        result = answer_question("买断是什么意思？")
        self.assertEqual(result["status"], "ready")
        self.assertIn("TERM-009", result["citations"])
        self.assertTrue(result["confirmation_required"])

    def test_unknown_answer_refuses(self):
        result = answer_question("火星插画协会会员费")
        self.assertEqual(result["status"], "no_answer")
        self.assertEqual(result["citations"], [])


if __name__ == "__main__":
    unittest.main()
