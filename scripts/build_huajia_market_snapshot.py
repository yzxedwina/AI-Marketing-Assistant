#!/usr/bin/env python3
"""Build a deterministic Huajia market snapshot and compare it with the prior snapshot."""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "collected" / "huajia"

def newest(pattern: str) -> Path | None:
    files = sorted(SOURCE_DIR.glob(pattern), reverse=True)
    return files[0] if files else None

def load(path: Path | None) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path else {}

def make_metrics(records: list[dict]) -> dict:
    prices = [r["price_yuan"] for r in records if isinstance(r.get("price_yuan"), (int, float))]
    sales = [r["sale_count"] for r in records if isinstance(r.get("sale_count"), (int, float))]
    categories = Counter(r.get("category_description") or "未分类" for r in records)
    return {"showcase_count": len(records), "median_price_yuan": median(prices) if prices else None,
            "total_visible_sales": sum(sales) if sales else None,
            "category_counts": dict(sorted(categories.items()))}

def compare(current: list[dict], previous: list[dict]) -> dict:
    current_by_id = {r["showcase_id"]: r for r in current}
    previous_by_id = {r["showcase_id"]: r for r in previous}
    common = set(current_by_id) & set(previous_by_id)
    price_changes, stock_changes = [], []
    for goods_id in sorted(common):
        before, after = previous_by_id[goods_id], current_by_id[goods_id]
        if before.get("price_yuan") != after.get("price_yuan"):
            price_changes.append({"showcase_id": goods_id, "before": before.get("price_yuan"), "after": after.get("price_yuan")})
        if before.get("stock") != after.get("stock"):
            stock_changes.append({"showcase_id": goods_id, "before": before.get("stock"), "after": after.get("stock")})
    return {"new_showcase_ids": sorted(set(current_by_id) - set(previous_by_id)),
            "missing_showcase_ids": sorted(set(previous_by_id) - set(current_by_id)),
            "price_changes": price_changes, "stock_changes": stock_changes,
            "comparison_note": "缺失仅表示本次采样未出现，不直接等同下架。"}

def main() -> int:
    list_path, detail_path = newest("showcases_*.json"), newest("showcase_details_*.json")
    list_payload, detail_payload = load(list_path), load(detail_path)
    if list_payload.get("collection_status") != "success":
        raise SystemExit("没有可用的画加橱窗列表结果")
    details = {r["showcase_id"]: r for r in detail_payload.get("records", [])}
    records = []
    for record in list_payload.get("records", []):
        merged = dict(record)
        for key, value in details.get(record.get("showcase_id"), {}).items():
            if value is not None and key not in {"raw_public_fields", "raw_detail_fields"}:
                merged[key] = value
        records.append(merged)
    prior_paths = sorted(SOURCE_DIR.glob("market_snapshot_*.json"), reverse=True)
    previous = load(prior_paths[0]) if prior_paths else {}
    now = datetime.now(timezone.utc)
    result = {"schema_version": "1.0.0", "source_platform": "huajia",
              "snapshot_status": "baseline" if not previous else "compared",
              "observed_at": now.isoformat(timespec="seconds"),
              "source_files": [p.name for p in (list_path, detail_path) if p],
              "sample_scope": {"showcases": len(records), "details": len(details), "not_full_market_census": True},
              "metrics": make_metrics(records),
              "comparison": compare(records, previous.get("records", [])) if previous else None,
              "records": records}
    output_path = SOURCE_DIR / f"market_snapshot_{now.strftime('%Y%m%d_%H%M%S')}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["snapshot_status"], "records": len(records), "output": str(output_path)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
