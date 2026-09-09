import unittest

from scripts.collect_huajia_showcases import normalize_goods_payload


class HuajiaShowcaseCollectorTests(unittest.TestCase):
    def test_normalizes_public_goods_payload(self):
        payload = {"data": {"goods_list": [{
            "id": "G001", "name": "宠物头像", "price": 6500,
            "user": {"uid": "A001", "name": "画师甲"},
            "tags": [{"tag": "头像"}, {"tag": "宠物"}],
            "favorite_count": 20, "sale_count": 3, "stock": 2, "status": 1,
            "category": 3, "category_desc": "头像", "delivery_delay_desc": "3天",
        }]}}
        result = normalize_goods_payload(payload, 5)
        self.assertEqual(result[0]["showcase_name"], "宠物头像")
        self.assertEqual(result[0]["price_yuan"], 65.0)
        self.assertEqual(result[0]["tags"], ["头像", "宠物"])
        self.assertEqual(result[0]["category_description"], "头像")
        self.assertEqual(result[0]["delivery_description"], "3天")


if __name__ == "__main__":
    unittest.main()
