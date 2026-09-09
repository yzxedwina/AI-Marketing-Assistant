import unittest

from backend.collectors.mihuashi_stalls import parse_stall_cards


class MihuashiStallTests(unittest.TestCase):
    def test_normalizes_and_limits_public_cards(self):
        rows = [
            {"url": "https://www.mihuashi.com/stalls/1", "text": "宠物水彩挂件\n画师甲\n¥ 100\n收藏 12\n已售 3", "title": "宠物水彩挂件", "artist": "画师甲"},
            {"url": "https://www.mihuashi.com/stalls/2", "text": "兽设场景插图\n画师乙\n￥600", "title": "兽设场景插图", "artist": "画师乙"},
        ]
        result = parse_stall_cards(rows, 1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price_display_cny"], 100.0)
        self.assertEqual(result[0]["favorite_count_display"], 12)
        self.assertEqual(result[0]["sales_count_display"], 3)

    def test_missing_numbers_remain_null(self):
        result = parse_stall_cards([{"url": "https://www.mihuashi.com/stalls/3", "text": "公开橱窗"}], 10)[0]
        self.assertIsNone(result["price_display_cny"])
        self.assertIsNone(result["sales_count_display"])

    def test_category_navigation_is_not_a_stall(self):
        rows = [{"url": "https://www.mihuashi.com/stalls/list?state=forsale&category=16", "text": "全部橱窗 头像"}]
        self.assertEqual(parse_stall_cards(rows, 10), [])


if __name__ == "__main__":
    unittest.main()
