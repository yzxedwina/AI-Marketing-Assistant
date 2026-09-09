#!/usr/bin/env python3
"""Read a few public Huajia showcase detail pages with Playwright."""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_HOST = "huajia.163.com"


def normalize_detail(payload: dict, source_url: str) -> dict | None:
    data = payload.get("data") or payload
    goods = data.get("goods") if isinstance(data, dict) else None
    if not isinstance(goods, dict):
        return None
    goods_id = str(goods.get("id") or goods.get("unique_id") or "").strip()
    name = re.sub(r"\s+", " ", str(goods.get("name") or "")).strip()
    if not goods_id or not name:
        return None
    user = goods.get("user") or goods.get("artist") or {}
    raw_price = goods.get("price")
    tags = goods.get("tags") or goods.get("show_tags") or goods.get("sub_channels") or []
    normalized_tags = []
    for tag in tags:
        normalized_tags.append(str(tag.get("tag") or tag.get("name") or tag.get("title") or "")
                               if isinstance(tag, dict) else str(tag))
    for field in ("styles", "techniques", "types", "prefer_labels", "refuse_labels"):
        for tag in goods.get(field) or []:
            normalized_tags.append(str(tag.get("tag") or tag.get("name") or tag.get("title") or tag.get("desc") or "")
                                   if isinstance(tag, dict) else str(tag))
    description = goods.get("description") or goods.get("intro") or goods.get("goods_desc")
    return {
        "showcase_id": goods_id,
        "showcase_name": name,
        "public_url": source_url,
        "artist_id": user.get("uid") or user.get("id"),
        "artist_name": user.get("name") or user.get("nickname"),
        "price_raw": raw_price,
        "price_yuan": round(raw_price / 100, 2) if isinstance(raw_price, (int, float)) else None,
        "category": goods.get("category"),
        "category_description": goods.get("category_desc"),
        "tags": list(dict.fromkeys(tag for tag in normalized_tags if tag)),
        "sale_count": goods.get("sold_count") or goods.get("sale_count"),
        "sale_count_description": goods.get("sold_count_desc") or goods.get("sales_desc"),
        "subscription_count": goods.get("subscription_count"),
        "favorite_count": goods.get("favorite_count") or goods.get("collect_count") or goods.get("wish_count"),
        "favorite_count_status": "not_publicly_exposed" if not any(
            key in goods for key in ("favorite_count", "collect_count", "wish_count")
        ) else "available",
        "stock": goods.get("stock"),
        "delivery_delay": goods.get("delivery_delay"),
        "delivery_description": goods.get("delivery_delay_desc") or goods.get("delivery_desc"),
        "description": str(description)[:3000] if description else None,
        "created_at": goods.get("add_time") or goods.get("create_time") or goods.get("created_at"),
        "updated_at": goods.get("update_time") or goods.get("updated_at"),
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_public_fields": sorted(goods.keys()),
        "raw_detail_fields": sorted(data.keys()),
    }


def latest_showcase_urls(limit: int) -> list[str]:
    files = sorted((ROOT / "data" / "collected" / "huajia").glob("showcases_*.json"), reverse=True)
    if not files:
        return []
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    return [record["public_url"] for record in payload.get("records", [])[:limit] if record.get("public_url")]


def main() -> int:
    parser = argparse.ArgumentParser(description="验证画加公开橱窗详情字段")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--min-wait", type=float, default=4.0)
    parser.add_argument("--max-wait", type=float, default=8.0)
    args = parser.parse_args()
    if not 1 <= args.limit <= 3:
        parser.error("详情验证 limit 必须在 1—3 之间")
    if args.min_wait < 3 or args.max_wait < args.min_wait:
        parser.error("等待区间必须满足 3 <= min-wait <= max-wait")
    urls = latest_showcase_urls(args.limit)
    if not urls:
        print("未找到橱窗列表结果，请先运行 collect_huajia_showcases.py", file=sys.stderr)
        return 2

    output_dir = ROOT / "data" / "collected" / "huajia"
    output_path = output_dir / f"showcase_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    records, diagnostics = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(locale="zh-CN", viewport={"width": 1440, "height": 1000})
            for source_url in urls:
                candidate_payloads: list[dict] = []
                response_log: list[dict] = []

                def inspect_response(response) -> None:
                    if response.request.resource_type not in {"xhr", "fetch"}:
                        return
                    if urlparse(response.url).hostname != ALLOWED_HOST:
                        return
                    response_log.append({"url": response.url, "status": response.status})
                    try:
                        payload = response.json()
                        data = payload.get("data") if isinstance(payload, dict) else None
                        if isinstance(data, dict) and isinstance(data.get("goods"), dict):
                            candidate_payloads.append(payload)
                    except (PlaywrightError, ValueError, TypeError):
                        pass

                page.on("response", inspect_response)
                response = page.goto(source_url, wait_until="domcontentloaded", timeout=30_000)
                wait_seconds = random.SystemRandom().uniform(args.min_wait, args.max_wait)
                page.wait_for_timeout(round(wait_seconds * 1000))
                record = normalize_detail(candidate_payloads[0], source_url) if candidate_payloads else None
                if record:
                    records.append(record)
                diagnostics.append({"url": source_url, "http_status": response.status if response else None,
                                    "page_title": page.title()[:180], "wait_seconds": round(wait_seconds, 2),
                                    "candidate_payload_count": len(candidate_payloads),
                                    "api_responses": response_log[:40]})
                page.remove_listener("response", inspect_response)
            browser.close()
        result = {"schema_version": "1.0.0", "source_platform": "huajia",
                  "record_type": "showcase_detail", "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "collection_status": "success" if len(records) == len(urls) else "partial_or_no_records",
                  "requested_count": len(urls), "collected_count": len(records), "records": records,
                  "limits": {"public_only": True, "login_used": False, "maximum_items": 3,
                             "concurrency": 1, "automatic_retries": 0}, "diagnostics": diagnostics}
    except (PlaywrightError, OSError) as error:
        result = {"schema_version": "1.0.0", "source_platform": "huajia", "record_type": "showcase_detail",
                  "collection_status": "blocked_or_failed", "collected_count": 0, "records": [],
                  "reason": re.sub(r"\s+", " ", str(error)).strip()[:300]}
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["collection_status"], "collected": result["collected_count"],
                      "output": str(output_path)}, ensure_ascii=False))
    return 0 if result["collection_status"] == "success" else 2


if __name__ == "__main__":
    sys.exit(main())
