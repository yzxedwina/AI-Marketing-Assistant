"""Normalization helpers for public Mihuashi stall cards."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable


def parse_stall_cards(cards: Iterable[Dict[str, Any]], limit: int) -> list[Dict[str, Any]]:
    output = []
    seen = set()
    for card in cards:
        url = str(card.get("url") or "").strip()
        text = re.sub(r"\s+", " ", str(card.get("text") or "")).strip()
        if re.search(r"/stalls(?:/list)?(?:\?|$)", url):
            continue
        if not url or url in seen or len(text) < 2:
            continue
        seen.add(url)
        price = re.search(r"(?:¥|￥)\s*(\d+(?:\.\d+)?)", text)
        favorites = re.search(r"(?:收藏|想要)\s*(\d+)", text)
        sold = re.search(r"(?:已售|成交)\s*(\d+)", text)
        output.append({
            "stall_id": re.sub(r"\W+", "-", url.rstrip("/").split("/")[-1]).strip("-") or None,
            "title": str(card.get("title") or text[:120]).strip()[:120],
            "artist_name": str(card.get("artist") or "").strip()[:80] or None,
            "public_url": url,
            "price_display_cny": float(price.group(1)) if price else None,
            "favorite_count_display": int(favorites.group(1)) if favorites else None,
            "sales_count_display": int(sold.group(1)) if sold else None,
            "visible_text": text[:800],
        })
        if len(output) >= limit:
            break
    return output
