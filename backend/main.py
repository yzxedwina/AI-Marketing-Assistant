import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from openai import APIStatusError, AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

from backend.auth import (
    AuthenticatedUser,
    auth_store,
    bearer,
    require_same_user,
    require_user,
)
from backend.memory import AnalysisRecordInput, OutcomeRecordInput, PreferenceInput, memory_store
from backend.profile import to_scoring_profile
from backend.rag import answer_question, search_knowledge
from backend.scoring import build_scoring_result, load_json, load_rules


load_dotenv()

app = FastAPI(title="AI Marketing Assistant API")
ROOT = Path(__file__).resolve().parents[1]
MARKET_DATA_DIR = Path(os.getenv("MARKET_DATA_DIR", str(ROOT / "data" / "collected")))
MARKET_REFRESH_COOLDOWN_SECONDS = int(os.getenv("MARKET_REFRESH_COOLDOWN_SECONDS", "1800"))
MARKET_REFRESH_LOCK = threading.Lock()
MARKET_REFRESH_STATE: Dict[str, Any] = {
    "status": "idle",
    "started_at": None,
    "completed_at": None,
    "message": "尚未从页面发起更新",
    "results": [],
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        item.strip()
        for item in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if item.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "Authorization"],
)


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=200)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=100)
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    profile: Dict[str, Any] = Field(default_factory=dict)


class ProfileCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=100)
    source_text: str = Field(default="", max_length=12000)


class OpportunityAIRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=100)
    candidate: Dict[str, Any]


class MarketingAIRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=100)
    candidate: Dict[str, Any]
    marketing_goal: Literal["流量增长", "吸引潜在客源", "增加客单"] = "流量增长"
    content_format: Literal["image_text", "video"]
    current_draft: Dict[str, Any] = Field(default_factory=dict)


class ReviewAIRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=100)
    goal: str = Field(min_length=1, max_length=200)
    direction: str = Field(min_length=1, max_length=200)
    metrics: Dict[str, Any]


class UIProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=200)
    direction: str = Field(min_length=1, max_length=300)
    customers: str = Field(min_length=1, max_length=500)
    topics: str = Field(min_length=1, max_length=500)
    styles: str = Field(min_length=1, max_length=500)
    services: str = Field(min_length=1, max_length=500)
    boundaries: str = Field(min_length=1, max_length=500)
    status: Literal["可接单", "交付中", "满载", "暂停"]
    capacity: str = Field(default="", max_length=100)
    manual_platform_data: Dict[str, Any] = Field(default_factory=dict)
    existing_businesses: list[Dict[str, Any]] = Field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _latest_collector_summary() -> dict:
    def latest(pattern: str) -> Optional[dict]:
        paths = sorted(ROOT.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
        if not paths:
            return None
        path = paths[0]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"file": path.name, "status": "unreadable", "records": 0}
        records = payload.get("records", [])
        if not records and isinstance(payload.get("results"), list):
            records = [record for group in payload["results"] for record in group.get("records", [])]
        return {
            "file": path.name,
            "status": payload.get("collection_status") or payload.get("access_status") or "available",
            "records": len(records),
            "updated_at": payload.get("generated_at") or payload.get("collected_at"),
        }

    huajia_paths = sorted(
        (MARKET_DATA_DIR / "huajia").glob("showcases_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    xhs_path = MARKET_DATA_DIR / "xiaohongshu_public_snapshot.json"

    def summarize_path(path: Optional[Path]) -> Optional[dict]:
        if path is None or not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"file": path.name, "status": "unreadable", "records": 0}
        records = payload.get("records", [])
        if not records and isinstance(payload.get("results"), list):
            records = [record for group in payload["results"] for record in group.get("records", [])]
        return {
            "file": path.name,
            "status": payload.get("collection_status") or payload.get("access_status") or "available",
            "records": len(records),
            "updated_at": payload.get("generated_at") or payload.get("collected_at"),
        }

    return {
        "huajia": summarize_path(huajia_paths[0] if huajia_paths else None),
        "xiaohongshu": summarize_path(xhs_path),
    }


def _run_market_refresh() -> None:
    MARKET_DATA_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".playwright-browsers"))
    commands = [
        (
            "画加公开橱窗",
            [
                sys.executable,
                str(ROOT / "scripts" / "collect_huajia_showcases.py"),
                "--limit", "20",
                "--min-wait", "4",
                "--max-wait", "8",
                "--output-dir", str(MARKET_DATA_DIR / "huajia"),
            ],
        ),
        (
            "小红书公开样本",
            [
                sys.executable,
                str(ROOT / "scripts" / "collect_xiaohongshu_public.py"),
                "--keywords", "手绘", "水彩", "兽设",
                "--limit", "20",
                "--total-limit", "20",
                "--vertical-only",
                "--wait-ms", "5000",
                "--load-timeout-ms", "30000",
                "--output", str(MARKET_DATA_DIR / "xiaohongshu_public_snapshot.json"),
            ],
        ),
    ]
    results = []
    for label, command in commands:
        try:
            completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=240, check=False)
            results.append({
                "source": label,
                "status": "completed" if completed.returncode == 0 else "limited_or_failed",
                "return_code": completed.returncode,
                "message": (completed.stdout or completed.stderr).strip()[-500:],
            })
        except subprocess.TimeoutExpired:
            results.append({"source": label, "status": "timeout", "message": "采集超过时间限制，已停止"})
        except OSError as error:
            results.append({"source": label, "status": "failed", "message": str(error)[:300]})
    with MARKET_REFRESH_LOCK:
        MARKET_REFRESH_STATE.update({
            "status": "completed",
            "completed_at": _utc_now(),
            "message": "数据更新已完成；受限来源会保留原有数据。",
            "results": results,
        })


@app.post("/market/refresh")
def start_market_refresh(
    background_tasks: BackgroundTasks,
    _current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    """Start one conservative, public-data refresh without blocking the UI."""
    with MARKET_REFRESH_LOCK:
        if MARKET_REFRESH_STATE["status"] == "running":
            return {**MARKET_REFRESH_STATE, "latest_data": _latest_collector_summary()}
        completed_at = MARKET_REFRESH_STATE.get("completed_at")
        if completed_at:
            completed = datetime.fromisoformat(completed_at)
            elapsed = (datetime.now(timezone.utc) - completed).total_seconds()
            if elapsed < MARKET_REFRESH_COOLDOWN_SECONDS:
                return {
                    **MARKET_REFRESH_STATE,
                    "message": "数据刚刚更新过，已复用最新结果。",
                    "cooldown_reused": True,
                    "latest_data": _latest_collector_summary(),
                }
        MARKET_REFRESH_STATE.update({
            "status": "running",
            "started_at": _utc_now(),
            "completed_at": None,
            "message": "正在更新画加与小红书公开数据",
            "results": [],
        })
    background_tasks.add_task(_run_market_refresh)
    return {**MARKET_REFRESH_STATE, "latest_data": _latest_collector_summary()}


@app.get("/market/refresh/status")
def get_market_refresh_status(
    _current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    with MARKET_REFRESH_LOCK:
        state = dict(MARKET_REFRESH_STATE)
    return {**state, "latest_data": _latest_collector_summary()}


def _split_ui_values(value: str) -> list[str]:
    normalized = value.replace("；", "、").replace("，", "、").replace(",", "、")
    return [item.strip() for item in normalized.split("、") if item.strip()]


def _first_number(value: Any) -> Optional[float]:
    import re
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else None


def _scored_opportunities(user_id: str) -> tuple[dict, dict]:
    demo_path = ROOT / "mock_data" / "opportunity_demo.json"
    memory = memory_store.load_context(user_id, history_limit=1)
    rich_profile = memory.get("confirmed_profile")
    if not rich_profile or rich_profile.get("profile_id") != user_id:
        raise HTTPException(status_code=404, detail="未找到该用户的已确认画像")
    scoring_profile = to_scoring_profile(rich_profile)
    demo = load_json(demo_path)
    market = [row for row in demo["market"] if row.get("source_platform") == "huajia"]
    result = build_scoring_result(scoring_profile, market, list(demo["trends"]), load_rules())
    return result, demo


COMPONENT_LABELS = {
    "profile_match": "画像匹配",
    "capacity_fit": "产能适配",
    "price_fit": "价格适配",
    "demand_signal": "需求信号",
    "competition_attractiveness": "竞争空间",
    "trend_relevance": "趋势相关性",
    "evidence_completeness": "证据完整度",
}
LEVEL_LABELS = {
    "recommended": "建议优先验证",
    "test": "可小范围测试",
    "observe": "建议继续观察",
    "not_recommended": "暂不建议",
}
CONFIDENCE_LABELS = {"high": "较高", "medium": "中等", "low": "偏低"}


def _opportunity_view(row: Dict[str, Any]) -> Dict[str, Any]:
    def labels(keys: list[str]) -> list[str]:
        return [COMPONENT_LABELS.get(key, key) for key in keys]
    return {
        "candidate_id": row["candidate_id"],
        "name": row["listing_name"],
        "category": row["category"],
        "score": row["opportunity_score"],
        "level": LEVEL_LABELS.get(row["recommendation_level"], row["recommendation_level"]),
        "confidence": CONFIDENCE_LABELS.get(row["confidence"], row["confidence"]),
        "eligible": row["eligible"],
        "components": [
            {"key": key, "label": COMPONENT_LABELS.get(key, key), "score": value}
            for key, value in row["components"].items()
        ],
        "support": labels(row["positive_factors"]),
        "risk": labels(row["negative_factors"]),
        "missing": labels(row["missing_information"]),
        "evidence_ids": row["evidence_ids"],
        "evidence_as_of": row["evidence_as_of"],
        "rule_version": row["rule_version"],
        "score_locked": True,
    }


def _deepseek_client() -> AsyncOpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI 服务尚未配置")
    return AsyncOpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        timeout=45.0,
        max_retries=0,
    )


def _allowed_ai_context(request_profile: Dict[str, Any], memory: dict) -> dict:
    """Return only user-authorized, task-relevant fields for third-party inference."""
    confirmed = memory.get("confirmed_profile") or {}
    return {
        "confirmed_profile": {
            "business_goals": confirmed.get("business_goals"),
            "creator_capabilities": confirmed.get("creator_capabilities"),
            "pricing_and_capacity": confirmed.get("pricing_and_capacity"),
        } if confirmed else request_profile,
        "confirmed_preferences": [
            {"key": item["key"], "value": item["value"]}
            for item in memory.get("confirmed_preferences", [])
        ],
        "recent_decisions": [
            {"analysis_type": item["analysis_type"], "result_id": item["result_id"]}
            for item in memory.get("analysis_history", [])[:2]
        ],
        "recent_outcomes": [
            {
                "direction": item["direction"],
                "platform": item["platform"],
                "metrics": item["metrics"],
                "capacity_status": item["capacity_status"],
            }
            for item in memory.get("outcome_history", [])[:2]
        ],
    }


async def _json_completion(system_prompt: str, payload: dict, *, max_tokens: int = 700) -> tuple[dict, dict]:
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    try:
        response = await _deepseek_client().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请根据以下输入输出 JSON：\n" + json.dumps(payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=max_tokens,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
    except APIStatusError as error:
        if error.status_code == 402:
            raise HTTPException(status_code=402, detail="DeepSeek API 余额不足，请充值后重试") from error
        if error.status_code == 401:
            raise HTTPException(status_code=503, detail="DeepSeek API 密钥无效或已失效") from error
        raise HTTPException(status_code=502, detail="DeepSeek API 请求失败，请稍后重试") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试") from error
    content = response.choices[0].message.content
    if not content:
        raise HTTPException(status_code=502, detail="AI 没有返回有效内容")
    try:
        result = json.loads(content)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=502, detail="AI 返回格式不符合要求，请重试") from error
    usage = response.usage
    return result, {
        "model": response.model or model,
        "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
    }


@app.post("/ai/profile-candidates")
async def ai_profile_candidates(
    request: ProfileCandidateRequest,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    user_id = require_same_user(request.user_id, current_user)
    memory = memory_store.load_context(user_id, history_limit=2)
    context = _allowed_ai_context({}, memory)
    result, usage = await _json_completion(
        """你是独立插画师用户画像分析助手。只生成候选判断，不能修改已确认事实。
严格输出 JSON 对象：candidates 数组中的每项必须包含 field、value、confidence、basis；confidence 只能为 high、medium、low；missing_information 为字符串数组。
仅根据输入资料判断。不得推断性格、收入或未授权内容；不得把候选业务写成用户已经擅长的业务。""",
        {"confirmed_context": context, "authorized_source_text": request.source_text},
        max_tokens=650,
    )
    candidates = result.get("candidates", [])[:6]
    for item in candidates:
        if not all(key in item for key in ("field", "value", "confidence", "basis")):
            raise HTTPException(status_code=502, detail="候选画像返回字段不完整")
    return {"candidates": candidates, "missing_information": result.get("missing_information", [])[:6], "usage": usage}


@app.post("/ai/opportunity-explanation")
async def ai_opportunity_explanation(
    request: OpportunityAIRequest,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    user_id = require_same_user(request.user_id, current_user)
    memory = memory_store.load_context(user_id, history_limit=2)
    context = _allowed_ai_context({}, memory)
    result, usage = await _json_completion(
        """你是商业机会解释助手。分数、等级和证据由规则系统提供，你不能计算、修改或新增数字。
严格输出 JSON：summary 字符串；supporting_reasons、counter_factors、missing_information、next_actions 均为字符串数组。
只能解释输入中的候选和证据；同时说明支持因素与反向因素；不能承诺曝光、咨询、成交或收入。""",
        {"confirmed_context": context, "rule_locked_candidate": request.candidate},
        max_tokens=600,
    )
    return {
        "summary": str(result.get("summary", ""))[:500],
        "supporting_reasons": result.get("supporting_reasons", [])[:5],
        "counter_factors": result.get("counter_factors", [])[:5],
        "missing_information": result.get("missing_information", [])[:5],
        "next_actions": result.get("next_actions", [])[:3],
        "locked_facts": request.candidate,
        "usage": usage,
    }


@app.get("/opportunities/score")
def get_opportunity_scores(
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    """Return deterministic, auditable scores. This endpoint never calls an LLM."""
    try:
        result, demo = _scored_opportunities(current_user.user_id)
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"评分输入不可用：{error}") from error

    analysis = result["opportunity_analysis"]
    eligible = [_opportunity_view(row) for row in analysis["opportunities"] if row["eligible"]]
    return {
        "status": analysis["status"],
        "profile_id": analysis["profile_id"],
        "rule_version": result["rule_version"],
        "data_mode": "mock_market_with_confirmed_profile",
        "data_notice": demo["notice"],
        "score_owner": "rule_engine",
        "llm_role": "explanation_only",
        "opportunities": eligible,
    }


@app.get("/workflow/context/{user_id}")
def get_workflow_context(
    user_id: str,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    """Single bootstrap payload used by the UI when returning to the product."""
    user_id = require_same_user(user_id, current_user)
    memory = memory_store.load_context(user_id, history_limit=10)
    try:
        result, demo = _scored_opportunities(user_id)
        opportunities = [
            _opportunity_view(row)
            for row in result["opportunity_analysis"]["opportunities"]
            if row["eligible"]
        ]
        scoring = {
            "status": result["opportunity_analysis"]["status"],
            "rule_version": result["rule_version"],
            "data_notice": demo["notice"],
            "opportunities": opportunities,
        }
    except (KeyError, TypeError, ValueError, HTTPException) as error:
        scoring = {"status": "unavailable", "error": str(error), "opportunities": []}
    return {"user_id": user_id, "memory": memory, "scoring": scoring}


@app.put("/workflow/profile/{user_id}")
def put_workflow_profile(
    user_id: str,
    request: UIProfileUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    """Merge UI-owned fields into the confirmed rich profile, then persist it."""
    user_id = require_same_user(user_id, current_user)
    baseline = load_json(ROOT / "config" / "profile_template.json")
    current = memory_store.load_context(user_id, history_limit=1).get("confirmed_profile")
    if not current:
        current = json.loads(json.dumps(baseline, ensure_ascii=False))
        current["profile_id"] = user_id
    updated = json.loads(json.dumps(current, ensure_ascii=False))
    updated["business_goals"]["primary_goal"] = request.goal
    updated["business_goals"]["target_direction"] = request.direction
    updated["business_goals"]["target_customers"] = _split_ui_values(request.customers)
    updated["business_goals"]["excluded_business"] = _split_ui_values(request.boundaries)
    updated["creator_capabilities"]["subjects"] = _split_ui_values(request.topics)
    updated["creator_capabilities"]["styles"] = _split_ui_values(request.styles)
    updated["creator_capabilities"]["services"] = _split_ui_values(request.services)
    updated["creator_capabilities"]["existing_businesses"] = request.existing_businesses
    weekly_hours = _first_number(request.capacity)
    if weekly_hours is not None:
        updated["pricing_and_capacity"]["weekly_commission_hours"] = weekly_hours
    products = []
    for business in request.existing_businesses:
        minimum = _first_number(business.get("priceMin"))
        maximum = _first_number(business.get("priceMax"))
        if business.get("name") and minimum is not None and maximum is not None:
            products.append({
                "product": business["name"],
                "price_min_cny": minimum,
                "price_max_cny": maximum,
                "weekly_capacity": _first_number(business.get("weeklyCapacity")),
                "delivery_range": business.get("durationRange") or None,
            })
    if products:
        updated["pricing_and_capacity"]["products"] = products
    updated.setdefault("platform_facts", {})["user_reported"] = request.manual_platform_data
    updated["profile_status"] = "confirmed"
    saved = memory_store.save_confirmed_profile(user_id, updated)
    capacity_map = {"可接单": "available", "交付中": "near_limit", "满载": "full", "暂停": "full"}
    memory_store.save_preference(
        user_id,
        PreferenceInput(key="capacity_status", value=capacity_map[request.status], source="user_edited"),
    )
    return {"saved": saved, "profile": updated, "ui_profile": request.model_dump()}


@app.post("/ai/marketing-plan")
async def ai_marketing_plan(
    request: MarketingAIRequest,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    user_id = require_same_user(request.user_id, current_user)
    memory = memory_store.load_context(user_id, history_limit=2)
    context = _allowed_ai_context({}, memory)
    format_schema = (
        "title_options 字符串数组、body 字符串、image_sequence 字符串数组、visual_notes 字符串"
        if request.content_format == "image_text"
        else "total_duration_seconds 正整数；video_script 对象数组，每项必须包含 start_time、end_time、duration_seconds、visual、voiceover；hook 字符串、caption 字符串"
    )
    result, usage = await _json_completion(
        f"""你是独立插画师营销文字方案助手。只围绕用户确认的商业方向生成可编辑草稿，不生成图片或视频，不自动发布，不承诺效果。
严格输出 JSON：strategy 对象包含 positioning、audience、selling_points 字符串数组、content_pillars 字符串数组、rhythm；content 对象包含 {format_schema}；risks 和 missing_information 为字符串数组。
所有策略和文字必须优先服务本轮营销目的，不得把流量增长、吸引潜在客源、增加客单三个目的混为一谈。
视频脚本必须给出总时长，并让每一段的起止时间、持续秒数、展示内容和口播文字相互对应。不得编造价格、销量、互动、增长率、日期或排名。内容形式已经确定，不得生成另一种形式。""",
        {"confirmed_context": context, "confirmed_candidate": request.candidate, "marketing_goal": request.marketing_goal, "content_format": request.content_format, "current_draft": request.current_draft},
        max_tokens=950,
    )
    return {"content_format": request.content_format, "strategy": result.get("strategy", {}), "content": result.get("content", {}), "risks": result.get("risks", [])[:5], "missing_information": result.get("missing_information", [])[:5], "usage": usage}


@app.post("/ai/outcome-review")
async def ai_outcome_review(
    request: ReviewAIRequest,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    user_id = require_same_user(request.user_id, current_user)
    memory = memory_store.load_context(user_id, history_limit=2)
    context = _allowed_ai_context({}, memory)
    result, usage = await _json_completion(
        """你是经营结果复盘助手。指标是用户回填事实；不得补写缺失数字、不得把相关性写成因果、不得承诺下一轮结果。
必须结合发布时间与当前观察时间判断数据积累时长；不同发布时间的内容不能只用累计绝对值直接比较。发布时间缺失时，明确列入 missing_information。
严格输出 JSON：summary 字符串；positive_signals、counter_signals、missing_information、next_actions 均为字符串数组。下一步最多三项。""",
        {"confirmed_context": context, "goal": request.goal, "direction": request.direction, "reported_metrics": request.metrics},
        max_tokens=550,
    )
    return {"summary": str(result.get("summary", ""))[:500], "positive_signals": result.get("positive_signals", [])[:5], "counter_signals": result.get("counter_signals", [])[:5], "missing_information": result.get("missing_information", [])[:5], "next_actions": result.get("next_actions", [])[:3], "usage": usage}


@app.post("/ai/chat")
async def ai_chat(
    request: ChatRequest,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    """Evidence-bounded multi-turn assistant for the creator workspace."""
    latest_question = request.messages[-1].content
    retrieval = search_knowledge(latest_question, top_k=3, minimum_score=0.12)
    evidence = retrieval.get("evidence", [])
    user_id = require_same_user(request.user_id, current_user)
    memory = memory_store.load_context(user_id, history_limit=3)
    ai_context = _allowed_ai_context(request.profile, memory)

    evidence_text = "\n".join(
        f"[{item['evidence_id']}] {item['title']}: {item['text']}" for item in evidence
    ) or "本轮未检索到直接相关的知识库证据。"
    system_prompt = f"""你是“AI 营销助手”中的营销助理，服务对象是独立插画师。
请使用简洁、自然的中文回答，并严格遵守：
1. 不编造市场数字、成交、平台规则、用户经历或确定性结论。
2. 只有下方明确提供的数据才可作为事实；缺失时直接说明缺失。
3. 区分用户已确认画像、候选判断和市场证据。候选判断不能写成事实。
4. 给建议时说明依据、反向因素和下一步；不要承诺流量、咨询或成交。
5. 若引用知识库内容，在对应句末标注 [证据ID]；没有相关证据时不要伪造引用。
6. 不代替用户发布、私信、接单或修改其长期画像。

用户已授权的画像与长期 Memory（仅限以下白名单字段）：
{json.dumps(ai_context, ensure_ascii=False)}
检索到的 RAG 证据：
{evidence_text}
"""
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    api_messages = [{"role": "system", "content": system_prompt}]
    api_messages.extend(message.model_dump() for message in request.messages[-8:])
    try:
        response = await _deepseek_client().chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=0.3,
            max_tokens=300,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
    except APIStatusError as error:
        if error.status_code == 402:
            raise HTTPException(status_code=402, detail="DeepSeek API 余额不足，请充值后重试") from error
        if error.status_code == 401:
            raise HTTPException(status_code=503, detail="DeepSeek API 密钥无效或已失效") from error
        raise HTTPException(status_code=502, detail="DeepSeek API 请求失败，请稍后重试") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试") from error

    reply = response.choices[0].message.content or "当前没有生成有效回答，请重试。"
    usage = response.usage
    return {
        "reply": reply,
        "model": response.model or model,
        "citations": [item["evidence_id"] for item in evidence],
        "rag_status": retrieval.get("status", "no_answer"),
        "memory_loaded": memory.get("has_memory", False),
        "usage": {
            "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
            "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
        },
    }


@app.post("/auth/login")
def login(request: LoginRequest) -> dict:
    authenticated = auth_store.authenticate(request.username, request.password)
    if not authenticated:
        raise HTTPException(status_code=401, detail="账号或密码不正确")
    token, user = authenticated
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
        },
    }


@app.get("/auth/me")
def auth_me(current_user: AuthenticatedUser = Depends(require_user)) -> dict:
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "display_name": current_user.display_name,
    }


@app.post("/auth/logout")
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    _current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    if credentials:
        auth_store.revoke(credentials.credentials)
    return {"status": "logged_out"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    index = ROOT / "frontend" / "dist" / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="前端尚未构建")
    return FileResponse(index)


@app.get("/rag/search")
def rag_search(
    q: str = Query(min_length=1, max_length=200),
    top_k: int = Query(default=5, ge=1, le=10),
    _current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    """Retrieve citable illustration-domain evidence; generation is a later step."""
    return search_knowledge(q, top_k=top_k)


@app.get("/rag/answer")
def rag_answer(
    q: str = Query(min_length=1, max_length=200),
    _current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    """Return a conservative cited answer without free-form model generation."""
    return answer_question(q)


@app.get("/memory/{user_id}")
def get_memory(
    user_id: str,
    history_limit: int = Query(default=10, ge=1, le=50),
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    """Load stable profile, preferences, and recent history on a return visit."""
    return memory_store.load_context(
        require_same_user(user_id, current_user),
        history_limit=history_limit,
    )


@app.put("/memory/{user_id}/profile")
def put_memory_profile(
    user_id: str,
    profile: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    user_id = require_same_user(user_id, current_user)
    try:
        return memory_store.save_confirmed_profile(user_id, profile)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.put("/memory/{user_id}/preferences")
def put_memory_preference(
    user_id: str,
    preference: PreferenceInput,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    user_id = require_same_user(user_id, current_user)
    return memory_store.save_preference(user_id, preference)


@app.post("/memory/{user_id}/analyses")
def post_memory_analysis(
    user_id: str,
    record: AnalysisRecordInput,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    user_id = require_same_user(user_id, current_user)
    return memory_store.add_analysis(user_id, record)


@app.post("/memory/{user_id}/outcomes")
def post_memory_outcome(
    user_id: str,
    record: OutcomeRecordInput,
    current_user: AuthenticatedUser = Depends(require_user),
) -> dict:
    user_id = require_same_user(user_id, current_user)
    return memory_store.add_outcome(user_id, record)


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_assets(full_path: str) -> FileResponse:
    """Serve the built Vite app and preserve client-side routes in production."""
    dist = (ROOT / "frontend" / "dist").resolve()
    candidate = (dist / full_path).resolve()
    if dist not in candidate.parents and candidate != dist:
        raise HTTPException(status_code=404, detail="Not Found")
    if candidate.is_file():
        return FileResponse(candidate)
    index = dist / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="前端尚未构建")
    return FileResponse(index)
