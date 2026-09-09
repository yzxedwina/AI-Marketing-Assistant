"""Conservative normalization helpers for public Mihuashi profile pages."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional


COUNT_PATTERNS = {
    "followers": (r"粉丝\s*([\d,.万wW]+)", r"([\d,.万wW]+)\s*粉丝"),
    "following": (r"关注\s*([\d,.万wW]+)", r"([\d,.万wW]+)\s*关注"),
    "likes": (r"获赞\s*([\d,.万wW]+)", r"([\d,.万wW]+)\s*获赞"),
}


def parse_compact_number(value: str) -> Optional[int]:
    cleaned = value.strip().replace(",", "").lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([万w]?)", cleaned)
    if not match:
        return None
    number = float(match.group(1))
    if match.group(2) in {"万", "w"}:
        number *= 10000
    return int(round(number))


def extract_labeled_counts(text: str) -> Dict[str, Optional[int]]:
    output: Dict[str, Optional[int]] = {}
    compact = re.sub(r"\s+", " ", text)
    for field, patterns in COUNT_PATTERNS.items():
        value = None
        for pattern in patterns:
            match = re.search(pattern, compact, flags=re.IGNORECASE)
            if match:
                value = parse_compact_number(match.group(1))
                break
        output[field] = value
    return output


def normalize_cards(cards: Iterable[Dict[str, Any]], limit: int) -> list[Dict[str, Any]]:
    seen = set()
    output = []
    for card in cards:
        url = str(card.get("url") or "").strip()
        text = re.sub(r"\s+", " ", str(card.get("text") or "")).strip()
        key = url or text
        if not key or key in seen or len(text) < 2:
            continue
        seen.add(key)
        price_match = re.search(r"(?:¥|￥)\s*(\d+(?:\.\d+)?)", text)
        output.append({
            "title": text[:120],
            "public_url": url or None,
            "price_display_cny": float(price_match.group(1)) if price_match else None,
            "visible_text": text[:500],
        })
        if len(output) >= limit:
            break
    return output
