import unittest

from scripts.collect_huajia_showcase_details import normalize_detail


class HuajiaShowcaseDetailCollectorTests(unittest.TestCase):
    def test_normalizes_detail_payload(self):
        payload = {"data": {"goods": {
            "id": "G1", "name": "动物头像", "price": 6500,
            "user": {"uid": "A1", "name": "画师甲"},
            "category_desc": "头像", "sold_count": 8, "stock": 2,
            "delivery_delay_desc": "3天", "description": "公开服务说明",
            "sub_channels": [{"name": "动物"}], "styles": [{"name": "水彩"}],
            "subscription_count": 12, "sold_count_desc": "已售8", "add_time": 100,
        }, "extras": {"tips": []}}}
        record = normalize_detail(payload, "https://huajia.163.com/main/goods/details/G1")
        self.assertEqual(record["price_yuan"], 65.0)
        self.assertEqual(record["tags"], ["动物", "水彩"])
        self.assertEqual(record["delivery_description"], "3天")
        self.assertEqual(record["subscription_count"], 12)
        self.assertEqual(record["sale_count_description"], "已售8")
        self.assertEqual(record["favorite_count_status"], "not_publicly_exposed")
        self.assertEqual(record["created_at"], 100)


if __name__ == "__main__":
    unittest.main()
