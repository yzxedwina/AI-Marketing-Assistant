import unittest

from backend.collectors.mihuashi import extract_labeled_counts, normalize_cards, parse_compact_number
from scripts.collect_mihuashi_public import safe_failure_reason, validate_loaded_page


class MihuashiCollectorTests(unittest.TestCase):
    def test_compact_number(self):
        self.assertEqual(parse_compact_number("3.6万"), 36000)
        self.assertEqual(parse_compact_number("1,234"), 1234)
        self.assertIsNone(parse_compact_number("未知"))

    def test_labeled_counts_do_not_invent_missing_fields(self):
        result = extract_labeled_counts("关注 42　粉丝 182")
        self.assertEqual(result["following"], 42)
        self.assertEqual(result["followers"], 182)
        self.assertIsNone(result["likes"])

    def test_card_limit_and_deduplication(self):
        rows = [
            {"url": "https://www.mihuashi.com/artworks/1", "text": "宠物水彩 ¥100"},
            {"url": "https://www.mihuashi.com/artworks/1", "text": "重复"},
            {"url": "https://www.mihuashi.com/artworks/2", "text": "兽设场景 ¥600"},
        ]
        result = normalize_cards(rows, limit=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["price_display_cny"], 100.0)

    def test_sandbox_failure_is_sanitized(self):
        reason = safe_failure_reason(RuntimeError("MachPortRendezvousServer: Permission denied (1100)"))
        self.assertEqual(reason, "browser_launch_blocked_by_local_sandbox")

    def test_profile_redirect_to_error_page_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "invalid_public_page_redirect"):
            validate_loaded_page(
                "https://www.mihuashi.com/profiles/899269?role=painter",
                "https://www.mihuashi.com/500/",
                "",
            )

    def test_valid_profile_url_is_accepted(self):
        validate_loaded_page(
            "https://www.mihuashi.com/profiles/899269?role=painter",
            "https://www.mihuashi.com/profiles/899269?role=painter",
            "EdwinaYYY 粉丝 182",
        )

    def test_artist_list_url_is_accepted(self):
        validate_loaded_page(
            "https://www.mihuashi.com/artists",
            "https://www.mihuashi.com/artists",
            "画师列表",
        )


if __name__ == "__main__":
    unittest.main()
