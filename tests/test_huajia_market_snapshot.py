import unittest
from scripts.build_huajia_market_snapshot import compare, make_metrics

class HuajiaMarketSnapshotTests(unittest.TestCase):
    def test_metrics_are_deterministic(self):
        rows = [{"price_yuan": 60.0, "sale_count": 10, "category_description": "头像"},
                {"price_yuan": 120.0, "sale_count": 5, "category_description": "插画"}]
        result = make_metrics(rows)
        self.assertEqual(result["median_price_yuan"], 90.0)
        self.assertEqual(result["total_visible_sales"], 15)

    def test_compares_ids_price_and_stock(self):
        previous = [{"showcase_id": "A", "price_yuan": 60, "stock": 2}]
        current = [{"showcase_id": "A", "price_yuan": 65, "stock": 1},
                   {"showcase_id": "B", "price_yuan": 80, "stock": 2}]
        result = compare(current, previous)
        self.assertEqual(result["new_showcase_ids"], ["B"])
        self.assertEqual(len(result["price_changes"]), 1)
        self.assertEqual(len(result["stock_changes"]), 1)

if __name__ == "__main__":
    unittest.main()
