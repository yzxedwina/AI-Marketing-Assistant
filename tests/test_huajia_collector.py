import unittest

from scripts.collect_huajia_public import normalize, normalize_artist_payload


class HuajiaCollectorTests(unittest.TestCase):
    def test_deduplicates_and_limits(self):
        rows = [
            {"url": "https://huajia.163.com/profile/1", "text": "画师甲 公开资料"},
            {"url": "https://huajia.163.com/profile/1", "text": "重复"},
            {"url": "https://huajia.163.com/profile/2", "text": "画师乙 公开资料"},
        ]
        result = normalize(rows, 2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "画师甲 公开资料")

    def test_excludes_artist_list_navigation_link(self):
        rows = [
            {"url": "https://huajia.163.com/board/artist/list/1", "text": "首页 约稿 橱窗 画师 作品"},
            {"url": "https://huajia.163.com/profile/123", "text": "画师甲 公开资料"},
        ]
        result = normalize(rows, 5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["public_url"], "https://huajia.163.com/profile/123")

    def test_normalizes_public_artist_api(self):
        payload = {"data": {"artist_list": [{
            "uid": "ABC123", "name": "画师甲", "artist_average_score": 4.9,
            "from_buyer_evaluation_count": 120, "online_goods_count": 6,
            "valid_work_count": 35, "artist_grade_tag": {"title": "优选画师"},
            "intro": "公开简介", "detailed_show_works": [
                {"show_tags": ["头像", "兽设"], "like_count": 18}
            ]
        }]}}
        result = normalize_artist_payload(payload, 5)
        self.assertEqual(result[0]["artist_name"], "画师甲")
        self.assertEqual(result[0]["online_showcase_count"], 6)
        self.assertEqual(result[0]["sample_work_tags"], ["兽设", "头像"])


if __name__ == "__main__":
    unittest.main()
