"""AI contracts: build evidence, validate model output, merge locked facts."""
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Set

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
DIGITS = re.compile(r"[0-9０-９]")


class Reason(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=160)
    evidence_ids: List[str] = Field(min_length=1)


class OpportunityExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0.0"]
    task: Literal["opportunity_explanation"]
    status: Literal["ready", "insufficient_evidence", "conflict", "blocked"]
    candidate_id: str
    summary: str = Field(min_length=1, max_length=180)
    supporting_reasons: List[Reason] = Field(max_length=5)
    counter_factors: List[Reason] = Field(max_length=5)
    missing_information: List[str] = Field(max_length=5)
    next_actions: List[str] = Field(min_length=1, max_length=3)
    citations: List[str]


def load_schema(name: str) -> Dict[str, Any]:
    return json.loads((ROOT / "config" / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))


def structured_output_format(name: str) -> Dict[str, Any]:
    return {"type": "json_schema", "name": name, "strict": True, "schema": load_schema(name)}


def build_opportunity_evidence(scoring_result: Dict[str, Any], candidate_id: str) -> Dict[str, Any]:
    analysis = scoring_result["opportunity_analysis"]
    candidate = next((x for x in analysis["opportunities"] if x["candidate_id"] == candidate_id), None)
    if candidate is None:
        raise ValueError(f"candidate_id 不存在: {candidate_id}")
    allowed = sorted(set(candidate["evidence_ids"]["market"] + candidate["evidence_ids"]["trends"]))
    return {
        "contract_version": "1.0.0", "task": "opportunity_explanation",
        "profile_id": analysis["profile_id"], "candidate_id": candidate_id,
        "input_status": analysis["status"],
        "locked_facts": {
            "rule_version": candidate["rule_version"], "opportunity_score": candidate["opportunity_score"],
            "recommendation_level": candidate["recommendation_level"], "confidence": candidate["confidence"],
            "components": candidate["components"], "evidence_as_of": candidate["evidence_as_of"]},
        "rule_trace": {key: candidate[key] for key in ("positive_factors", "negative_factors", "missing_information")},
        "allowed_evidence_ids": allowed, "evidence": candidate["evidence_ids"],
        "constraints": {"numbers_in_generated_text_forbidden": True, "effect_promises_forbidden": True, "external_actions_forbidden": True}
    }


def _strings(value: Any) -> Iterable[str]:
    """Yield generated prose only; identifiers are allowed to contain digits."""
    if isinstance(value, str): yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            if key not in {"schema_version", "task", "candidate_id", "evidence_ids", "citations"}:
                yield from _strings(child)
    elif isinstance(value, list):
        for child in value: yield from _strings(child)


def _citations(output: Dict[str, Any]) -> Set[str]:
    used = set(output.get("citations", []))
    for key in ("supporting_reasons", "counter_factors"):
        for item in output.get(key, []): used.update(item.get("evidence_ids", []))
    return used


def validate_ai_output(output: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    validated = OpportunityExplanation.model_validate(output).model_dump()
    if validated["candidate_id"] != evidence["candidate_id"]:
        raise ValueError("candidate_id 与输入不一致")
    illegal = _citations(validated) - set(evidence["allowed_evidence_ids"])
    if illegal: raise ValueError(f"引用了白名单外证据: {sorted(illegal)}")
    if any(DIGITS.search(text) for text in _strings(validated)):
        raise ValueError("AI 文案包含数字；事实数字必须由 locked_facts 展示")
    if validated["status"] == "ready" and not validated["citations"]:
        raise ValueError("ready 状态必须至少引用一个合法证据")
    return validated


def compose_user_result(output: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    return {"candidate_id": evidence["candidate_id"], "locked_facts": evidence["locked_facts"],
            "ai_content": output, "contract_version": evidence["contract_version"]}
