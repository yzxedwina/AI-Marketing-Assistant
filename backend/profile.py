"""Structured user-profile schema. AI suggestions remain unconfirmed until user approval."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class CandidateInference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    value: Any
    confidence: Literal["high", "medium", "low"]
    basis: List[str] = Field(min_length=1)


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0.0"]
    profile_id: str
    profile_status: Literal["pending_user_confirmation", "confirmed", "rejected"]
    confirmed_at: Optional[str] = None
    confirmed_fields: List[str] = Field(default_factory=list)
    display_names: Dict[str, str]
    business_goals: Dict[str, Any]
    creator_capabilities: Dict[str, Any]
    pricing_and_capacity: Dict[str, Any]
    portfolio_summary: Dict[str, Any]
    platform_facts: Dict[str, Any]
    candidate_inferences_requiring_confirmation: List[CandidateInference]
    missing_information: List[str]


def confirm_profile(profile: Dict[str, Any], approved_fields: List[str]) -> Dict[str, Any]:
    """Confirm only when every AI-inferred field is explicitly approved."""
    parsed = UserProfile.model_validate(profile)
    inferred = {item.field for item in parsed.candidate_inferences_requiring_confirmation}
    if inferred != set(approved_fields):
        raise ValueError("必须逐项确认或修改全部 AI 推断字段")
    result = parsed.model_dump()
    result["profile_status"] = "confirmed"
    result["confirmed_fields"] = sorted(inferred)
    return result


def to_scoring_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Convert the confirmed rich profile to the stable scoring input contract."""
    parsed = UserProfile.model_validate(profile)
    if parsed.profile_status != "confirmed":
        raise ValueError("只有已确认画像可以进入 Opportunity Score")
    products = parsed.pricing_and_capacity["products"]
    return {
        "profile_id": parsed.profile_id,
        "current_goal": parsed.business_goals["primary_goal"],
        "style_topics": ",".join(parsed.creator_capabilities["subjects"] + parsed.creator_capabilities["styles"]),
        "accepted_business": ",".join(parsed.creator_capabilities["services"]),
        "excluded_business": ",".join(parsed.business_goals["excluded_business"]),
        "target_price_min_cny": min(item["price_min_cny"] for item in products),
        "target_price_max_cny": max(item["price_max_cny"] for item in products),
        "service_price_ranges": {
            item["product"]: {
                "price_min_cny": item["price_min_cny"],
                "price_max_cny": item["price_max_cny"],
            }
            for item in products
        },
        "weekly_capacity_hours": parsed.pricing_and_capacity["weekly_commission_hours"],
        "weekly_marketing_hours": parsed.pricing_and_capacity["weekly_marketing_hours"],
        "required_medium": "traditional",
        "profile_version": 1,
        "profile_confirmed": True,
        "profile_confirmed_at": parsed.confirmed_at
    }
