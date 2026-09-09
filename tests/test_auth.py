import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from backend.auth import AuthStore, require_same_user
from backend.memory import AnalysisRecordInput, MemoryStore


class AuthIsolationTests(unittest.TestCase):
    def test_accounts_get_distinct_sessions_and_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "trial.sqlite3"
            auth = AuthStore(db_path)
            memory = MemoryStore(db_path)
            self.assertTrue(auth.create_account("u1", "friend01", "Password-0001", "用户一"))
            self.assertTrue(auth.create_account("u2", "friend02", "Password-0002", "用户二"))

            token1, user1 = auth.authenticate("friend01", "Password-0001")
            token2, user2 = auth.authenticate("friend02", "Password-0002")
            self.assertNotEqual(token1, token2)
            self.assertEqual(auth.session_user(token1).user_id, "u1")
            self.assertEqual(auth.session_user(token2).user_id, "u2")

            memory.add_analysis(
                "u1",
                AnalysisRecordInput(
                    analysis_type="opportunity",
                    result_id="only-u1",
                    result={"name": "用户一的数据"},
                ),
            )
            self.assertEqual(len(memory.load_context("u1")["analysis_history"]), 1)
            self.assertEqual(memory.load_context("u2")["analysis_history"], [])
            self.assertEqual(require_same_user("u1", user1), "u1")
            with self.assertRaises(HTTPException):
                require_same_user("u1", user2)

    def test_wrong_password_and_revoked_session_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            auth = AuthStore(Path(directory) / "trial.sqlite3")
            auth.create_account("u1", "friend01", "Password-0001", "用户一")
            self.assertIsNone(auth.authenticate("friend01", "wrong-password"))
            token, _user = auth.authenticate("friend01", "Password-0001")
            auth.revoke(token)
            self.assertIsNone(auth.session_user(token))


if __name__ == "__main__":
    unittest.main()
