#!/usr/bin/env python3
"""Small read-only Playwright probe for Huajia's public showcase list."""

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
SOURCE_URL = "https://huajia.163.com/main/goods"
ALLOWED_HOST = "huajia.163.com"


def first_value(item: dict, *keys):
    for key in keys:
        value = item.get(key)
        if value is not None:
            return value
    return None


def normalize_goods_payload(payload: dict, limit: int) -> list[dict]:
    data = payload.get("data") or payload
    goods_list = data.get("goods_list") or data.get("list") or []
    records = []
    for item in goods_list[:limit]:
        goods_id = str(first_value(item, "id", "goods_id", "unique_id") or "").strip()
        name = re.sub(r"\s+", " ", str(first_value(item, "name", "title", "goods_name") or "")).strip()
        if not goods_id or not name:
            continue
        user = item.get("user") or item.get("artist") or {}
        tags = first_value(item, "tags", "show_tags", "labels") or []
        normalized_tags = []
        for tag in tags:
            normalized_tags.append(str(tag.get("tag") or tag.get("name") or "") if isinstance(tag, dict) else str(tag))
        raw_price = first_value(item, "price", "min_price", "starting_price")
        records.append({
            "showcase_id": goods_id,
            "showcase_name": name,
            "public_url": f"https://{ALLOWED_HOST}/main/goods/details/{goods_id}",
            "artist_id": first_value(user, "uid", "id", "unique_id"),
            "artist_name": first_value(user, "name", "nickname"),
            "price_raw": raw_price,
            "price_yuan": round(raw_price / 100, 2) if isinstance(raw_price, (int, float)) else None,
            "original_price_raw": item.get("original_price"),
            "category": item.get("category"),
            "category_description": item.get("category_desc"),
            "tags": [tag for tag in normalized_tags if tag],
            "favorite_count": first_value(item, "favorite_count", "collect_count", "wish_count"),
            "sale_count": first_value(item, "sale_count", "sold_count", "order_count"),
            "stock": first_value(item, "stock", "stock_count", "remain_count"),
            "status": first_value(item, "status", "sale_status"),
            "sales_description": item.get("sales_desc"),
            "delivery_description": item.get("delivery_delay_desc"),
            "scheduled_sale_time": item.get("scheduled_sale_time"),
            "scheduled_sale_description": item.get("scheduled_sale_time_desc"),
            "is_template": item.get("is_template"),
            "raw_public_fields": sorted(item.keys()),
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="验证画加公开橱窗的小规模结构化读取能力")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--min-wait", type=float, default=4.0)
    parser.add_argument("--max-wait", type=float, default=8.0)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "collected" / "huajia")
    args = parser.parse_args()
    if not 1 <= args.limit <= 20:
        parser.error("验证阶段 limit 必须在 1—20 之间")
    if args.min_wait < 3 or args.max_wait < args.min_wait:
        parser.error("等待区间必须满足 3 <= min-wait <= max-wait")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"showcases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result = {"schema_version": "1.0.0", "source_platform": "huajia", "record_type": "showcase",
              "source_url": SOURCE_URL, "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(locale="zh-CN", viewport={"width": 1440, "height": 1000})
            candidate_payloads: list[dict] = []
            api_responses: list[dict] = []

            def inspect_response(response) -> None:
                if response.request.resource_type not in {"xhr", "fetch"}:
                    return
                if urlparse(response.url).hostname != ALLOWED_HOST:
                    return
                api_responses.append({"url": response.url, "status": response.status})
                try:
                    payload = response.json()
                    data = payload.get("data") if isinstance(payload, dict) else None
                    if isinstance(data, dict) and isinstance(data.get("goods_list"), list):
                        candidate_payloads.append(payload)
                except (PlaywrightError, ValueError, TypeError):
                    pass

            page.on("response", inspect_response)
            response = page.goto(SOURCE_URL, wait_until="domcontentloaded", timeout=30_000)
            wait_seconds = random.SystemRandom().uniform(args.min_wait, args.max_wait)
            page.wait_for_timeout(round(wait_seconds * 1000))
            page.mouse.wheel(0, 700)
            page.wait_for_timeout(1200)
            body = page.locator("body").inner_text(timeout=10_000)
            records = normalize_goods_payload(candidate_payloads[0], args.limit) if candidate_payloads else []
            result.update({
                "final_url": page.url,
                "http_status": response.status if response else None,
                "collection_status": "success" if records else "no_public_records",
                "collected_count": len(records),
                "records": records,
                "limits": {"public_only": True, "login_used": False, "maximum_items": args.limit,
                           "concurrency": 1, "automatic_retries": 0, "wait_seconds": round(wait_seconds, 2)},
                "diagnostics": {"page_title": page.title()[:160],
                                "body_excerpt": re.sub(r"\s+", " ", body).strip()[:1200],
                                "api_responses": api_responses[:50],
                                "candidate_payload_count": len(candidate_payloads)},
            })
            browser.close()
    except (PlaywrightError, RuntimeError, OSError) as error:
        result.update({"collection_status": "blocked_or_failed", "collected_count": 0, "records": [],
                       "reason": re.sub(r"\s+", " ", str(error)).strip()[:300]})
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["collection_status"], "collected": result["collected_count"],
                      "output": str(output_path)}, ensure_ascii=False))
    return 0 if result["collection_status"] == "success" else 2


if __name__ == "__main__":
    sys.exit(main())
