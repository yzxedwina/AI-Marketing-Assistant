"""Deterministic business scoring for the AI Marketing Assistant demo."""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "config" / "scoring_rules.json"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_rules(path: Path = DEFAULT_RULES) -> Dict[str, Any]:
    return load_json(path)


def _round(value: float, places: int = 2) -> float:
    unit = Decimal("1").scaleb(-places)
    return float(Decimal(str(value)).quantize(unit, rounding=ROUND_HALF_UP))


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _tokens(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        parts = value
    else:
        parts = re.split(r"[,，、;/|\s]+", str(value))
    return sorted({str(part).strip().lower() for part in parts if str(part).strip()})


def _percentile_scores(records: Sequence[Dict[str, Any]], field: str) -> Dict[str, float]:
    """Return stable 0..100 mid-rank percentiles keyed by post_id."""
    ordered = sorted(records, key=lambda row: (float(row.get(field) or 0), str(row["post_id"])))
    count = len(ordered)
    if count <= 1:
        return {str(row["post_id"]): 50.0 for row in ordered}
    values: Dict[float, List[int]] = {}
    for index, row in enumerate(ordered):
        values.setdefault(float(row.get(field) or 0), []).append(index)
    result: Dict[str, float] = {}
    for row in ordered:
        positions = values[float(row.get(field) or 0)]
        mid_rank = sum(positions) / len(positions)
        result[str(row["post_id"])] = 100 * mid_rank / (count - 1)
    return result


def classify_level(score: float, levels: Dict[str, float]) -> str:
    if "hot" in levels:
        return "hot" if score >= levels["hot"] else "watch" if score >= levels["watch"] else "normal"
    return (
        "recommended" if score >= levels["recommended"] else
        "test" if score >= levels["test"] else
        "observe" if score >= levels["observe"] else "not_recommended"
    )


def score_hotspots(records: Sequence[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    cfg = rules["hotspot"]
    stable_records = sorted(deepcopy(list(records)), key=lambda row: str(row["post_id"]))
    if not stable_records:
        return []
    likes = _percentile_scores(stable_records, "like_count")
    favorites = _percentile_scores(stable_records, "favorite_count")
    comments = _percentile_scores(stable_records, "comment_count")
    rate_rows = []
    for row in stable_records:
        denominator = max(float(row.get("author_follower_count") or 0), 1.0)
        rate = (float(row.get("like_count") or 0) + float(row.get("favorite_count") or 0) + float(row.get("comment_count") or 0)) / denominator
        rate_rows.append({"post_id": row["post_id"], "engagement_rate": rate})
    rates = _percentile_scores(rate_rows, "engagement_rate")
    weights = cfg["weights"]
    output = []
    for row in stable_records:
        post_id = str(row["post_id"])
        snapshot = _parse_time(row["interaction_snapshot_at"])
        published = _parse_time(row["published_at"])
        age_days = max((snapshot.date() - published.date()).days, 0)
        recency = max(0.0, 100 * (1 - age_days / cfg["recency_window_days"]))
        relevance = 100 * float(row.get("illustration_relevance") or 0)
        components = {
            "likes": likes[post_id], "favorites": favorites[post_id],
            "comments": comments[post_id], "engagement_rate": rates[post_id],
            "recency": recency, "illustration_relevance": relevance,
        }
        score = sum(components[name] * weights[name] for name in weights)
        level = classify_level(score, cfg["levels"])
        business_status = level if relevance >= 100 * cfg["business_relevance_min"] else "mass_hot_low_relevance"
        output.append({
            "post_id": post_id, "hotspot_score": _round(score), "hotspot_level": level,
            "business_status": business_status,
            "components": {key: _round(value) for key, value in components.items()},
            "evidence_as_of": row["interaction_snapshot_at"], "rule_version": rules["rule_version"],
        })
    return sorted(output, key=lambda row: (-row["hotspot_score"], row["post_id"]))


def _weighted_engagement(row: Dict[str, Any], weights: Dict[str, float]) -> float:
    return sum(float(row.get(field[:-1] + "_count") or 0) * weight for field, weight in weights.items())


def detect_abnormal_growth(records: Sequence[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    cfg = rules["abnormal_growth"]
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in records:
        grouped.setdefault(str(row["post_id"]), []).append(row)
    output = []
    for post_id in sorted(grouped):
        snapshots = sorted(grouped[post_id], key=lambda row: row["interaction_snapshot_at"])
        if len(snapshots) < 2:
            output.append({"post_id": post_id, "status": "insufficient_history", "reason": "至少需要两次互动快照", "rule_version": rules["rule_version"]})
            continue
        previous, current = snapshots[-2], snapshots[-1]
        hours = (_parse_time(current["interaction_snapshot_at"]) - _parse_time(previous["interaction_snapshot_at"])).total_seconds() / 3600
        if hours < cfg["minimum_interval_hours"] or hours > cfg["maximum_interval_hours"]:
            output.append({"post_id": post_id, "status": "invalid_interval", "interval_hours": _round(hours), "rule_version": rules["rule_version"]})
            continue
        prior_total = _weighted_engagement(previous, cfg["engagement_weights"])
        current_total = _weighted_engagement(current, cfg["engagement_weights"])
        delta = current_total - prior_total
        growth_rate = delta / max(prior_total, cfg["small_base_floor"])
        velocity = delta / hours
        comment_share = float(current.get("comment_count") or 0) / max(current_total, 1)
        suspicious = growth_rate >= cfg["suspicious_growth_rate"] and comment_share < cfg["suspicious_comment_share_max"]
        abnormal = (
            current_total >= cfg["minimum_weighted_engagement"] and
            growth_rate >= cfg["minimum_growth_rate"] and
            velocity >= cfg["minimum_velocity_per_hour"] and not suspicious
        )
        output.append({
            "post_id": post_id,
            "status": "needs_review" if suspicious else "abnormal_growth" if abnormal else "normal_growth",
            "interval_hours": _round(hours), "weighted_engagement": _round(current_total),
            "growth_rate": _round(growth_rate), "velocity_per_hour": _round(velocity),
            "rule_version": rules["rule_version"],
        })
    return output


def _expanded_business(profile: Dict[str, Any], aliases: Dict[str, List[str]]) -> set:
    result = set(_tokens(profile.get("accepted_business")))
    for item in list(result):
        result.update(token.lower() for token in aliases.get(item, []))
    return result


def _price_fit(profile: Dict[str, Any], listing: Dict[str, Any]) -> Optional[float]:
    category_range = (profile.get("service_price_ranges") or {}).get(listing.get("category"), {})
    values = [
        category_range.get("price_min_cny", profile.get("target_price_min_cny")),
        category_range.get("price_max_cny", profile.get("target_price_max_cny")),
        listing.get("price_min_cny"),
        listing.get("price_max_cny"),
    ]
    if any(value is None for value in values):
        return None
    p_min, p_max, m_min, m_max = map(float, values)
    overlap = max(0.0, min(p_max, m_max) - max(p_min, m_min))
    union = max(p_max, m_max) - min(p_min, m_min)
    if overlap > 0:
        return 100 * overlap / max(union, 1)
    gap = max(m_min - p_max, p_min - m_max, 0)
    return max(0.0, 100 * (1 - gap / max(p_max, m_max, 1)))


def _matches(listing: Dict[str, Any], trend: Dict[str, Any]) -> bool:
    market_tokens = set(_tokens(listing.get("category")) + _tokens(listing.get("tags")) + _tokens(listing.get("listing_name")))
    trend_text = (str(trend.get("title", "")) + "," + str(trend.get("topic_tags", ""))).lower()
    return any(len(token) >= 2 and token in trend_text for token in market_tokens)


def score_opportunities(profile: Dict[str, Any], market: Sequence[Dict[str, Any]], trends: Sequence[Dict[str, Any]], rules: Dict[str, Any]) -> Dict[str, Any]:
    if not profile.get("profile_confirmed"):
        return {"profile_id": profile.get("profile_id"), "status": "blocked", "reason": "用户画像尚未确认", "opportunities": [], "rule_version": rules["rule_version"]}
    cfg = rules["opportunity"]
    accepted = _expanded_business(profile, cfg["business_aliases"])
    excluded = set(_tokens(profile.get("excluded_business")))
    hotspot_map = {row["post_id"]: row for row in score_hotspots(trends, rules)}
    opportunities = []
    for listing in sorted(market, key=lambda row: str(row["listing_id"])):
        listing_text = (str(listing.get("listing_name", "")) + "," + str(listing.get("category", "")) + "," + str(listing.get("tags", ""))).lower()
        exclusion_hits = sorted(token for token in excluded if token and token in listing_text)
        if exclusion_hits:
            continue
        category = str(listing.get("category", "")).lower()
        listing_tokens = set(_tokens(listing.get("tags")) + [category])
        shared = accepted.intersection(listing_tokens)
        profile_match = min(100.0, (70.0 if category in accepted else 0.0) + 15.0 * len(shared))
        blocking_reasons = []
        if profile_match < cfg["minimum_profile_match"]:
            blocking_reasons.append("product_form_mismatch")
        required_medium = profile.get("required_medium")
        listing_medium = listing.get("medium")
        if required_medium and cfg["require_known_medium_when_profile_restricts_medium"]:
            if not listing_medium:
                blocking_reasons.append("medium_missing")
            elif listing_medium != required_medium:
                blocking_reasons.append("medium_mismatch")
        effort = cfg["category_effort_hours"].get(listing.get("category"))
        capacity = profile.get("weekly_capacity_hours")
        capacity_fit = None if effort is None or capacity is None else min(100.0, 100 * float(capacity) / float(effort))
        price_fit = _price_fit(profile, listing)
        sales = listing.get("sales_count")
        favorites = listing.get("favorite_count")
        demand = None if sales is None or favorites is None else 50 * min(float(sales) / cfg["demand_caps"]["sales_count"], 1) + 50 * min(float(favorites) / cfg["demand_caps"]["favorite_count"], 1)
        count = listing.get("same_category_count")
        competition = None if count is None else 100 * (1 - min(float(count) / cfg["competition_count_cap"], 1))
        matching = [trend for trend in trends if _matches(listing, trend)]
        trend_score = max((hotspot_map[str(trend["post_id"])]["hotspot_score"] * float(trend.get("illustration_relevance") or 0) for trend in matching), default=0.0)
        required_present = [listing.get("category"), listing.get("price_min_cny"), listing.get("price_max_cny"), sales, favorites, count]
        completeness = 100 * sum(value is not None and value != "" for value in required_present) / len(required_present)
        components = {
            "profile_match": profile_match, "capacity_fit": capacity_fit, "price_fit": price_fit,
            "demand_signal": demand, "competition_attractiveness": competition,
            "trend_relevance": trend_score, "evidence_completeness": completeness,
        }
        active = {key: value for key, value in components.items() if value is not None}
        active_weight = sum(cfg["weights"][key] for key in active)
        score = sum(value * cfg["weights"][key] / active_weight for key, value in active.items())
        missing = sorted(key for key, value in components.items() if value is None)
        confidence_value = completeness
        confidence = "high" if confidence_value >= cfg["confidence"]["high"] else "medium" if confidence_value >= cfg["confidence"]["medium"] else "low"
        positives = [name for name, value in active.items() if value >= 70]
        negatives = [name for name, value in active.items() if value < 40]
        eligible = not blocking_reasons
        opportunities.append({
            "candidate_id": str(listing["listing_id"]), "listing_name": listing.get("listing_name"),
            "category": listing.get("category"), "eligible": eligible,
            "eligibility_status": "eligible" if eligible else "ineligible",
            "blocking_reasons": sorted(blocking_reasons),
            "opportunity_score": _round(score) if eligible else None,
            "recommendation_level": classify_level(score, cfg["levels"]) if eligible else "ineligible",
            "confidence": confidence,
            "components": {key: None if value is None else _round(value) for key, value in components.items()},
            "applied_weights": {key: _round(cfg["weights"][key] / active_weight, 4) for key in active},
            "positive_factors": sorted(positives), "negative_factors": sorted(negatives),
            "missing_information": missing,
            "evidence_ids": {"market": [str(listing["listing_id"])], "trends": sorted(str(row["post_id"]) for row in matching)},
            "evidence_as_of": listing.get("collected_at"), "rule_version": rules["rule_version"],
        })
    opportunities.sort(key=lambda row: (not row["eligible"], -(row["opportunity_score"] or 0), row["candidate_id"]))
    return {"profile_id": profile.get("profile_id"), "status": "ok", "opportunities": opportunities, "rule_version": rules["rule_version"]}


def build_scoring_result(profile: Dict[str, Any], market: Sequence[Dict[str, Any]], trends: Sequence[Dict[str, Any]], rules: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rule_version": rules["rule_version"],
        "data_mode": "mock" if all(row.get("is_mock") for row in list(market) + list(trends) + [profile]) else "mixed_or_real",
        "hotspots": score_hotspots(trends, rules),
        "abnormal_growth": detect_abnormal_growth(trends, rules),
        "opportunity_analysis": score_opportunities(profile, market, trends, rules),
    }
