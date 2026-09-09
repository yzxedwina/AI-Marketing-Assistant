"""Small, deterministic RAG baseline for illustration-domain knowledge."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "knowledge_base"
INDEX_PATH = KB_DIR / "index" / "chunks.json"
TOKEN_RE = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]")


def _tokens(text: str) -> list[str]:
    normalized = text.lower().strip()
    units = TOKEN_RE.findall(normalized)
    chinese = [item for item in units if "\u4e00" <= item <= "\u9fff"]
    latin = [item for item in units if item not in chinese]
    bigrams = [chinese[i] + chinese[i + 1] for i in range(len(chinese) - 1)]
    return latin + chinese + bigrams


def load_index(path: Path = INDEX_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError("知识索引不存在，请先运行 scripts/build_knowledge_index.py")
    return json.loads(path.read_text(encoding="utf-8"))


def search_knowledge(
    query: str,
    *,
    top_k: int = 5,
    knowledge_types: list[str] | None = None,
    platform: str | None = None,
    minimum_score: float = 0.08,
) -> dict[str, Any]:
    """Return cited chunks. This function does retrieval only; it does not invent an answer."""
    if not query.strip():
        return {"status": "need_input", "query": query, "evidence": [], "index_version": None}
    index = load_index()
    chunks = [item for item in index["chunks"] if item.get("status") != "inactive"]
    if knowledge_types:
        chunks = [item for item in chunks if item["knowledge_type"] in knowledge_types]
    if platform:
        chunks = [item for item in chunks if item.get("platform") in {None, platform}]
    query_tokens = Counter(_tokens(query))
    if not query_tokens or not chunks:
        return {"status": "no_answer", "query": query, "evidence": [], "index_version": index["index_version"]}

    document_frequency = Counter()
    for item in chunks:
        document_frequency.update(set(item["tokens"]))
    scored = []
    for item in chunks:
        token_counts = Counter(item["tokens"])
        score = 0.0
        for token, q_count in query_tokens.items():
            if token not in token_counts:
                continue
            idf = math.log((len(chunks) + 1) / (document_frequency[token] + 1)) + 1
            score += q_count * (1 + math.log(token_counts[token])) * idf
        searchable = item["searchable_text"].lower()
        for phrase in [query.strip().lower(), *item.get("aliases", [])]:
            if len(phrase) >= 2 and phrase in query.lower() and phrase in searchable:
                score += 4.0
        norm = max(len(query_tokens), 1) * 5
        normalized_score = score / norm
        if normalized_score >= minimum_score:
            scored.append((normalized_score, item))
    scored.sort(key=lambda pair: (-pair[0], -pair[1]["authority_rank"], pair[1]["knowledge_id"]))
    evidence = []
    for score, item in scored[: max(1, min(top_k, 10))]:
        evidence.append({
            "evidence_id": item["knowledge_id"],
            "title": item["title"],
            "text": item["text"],
            "knowledge_type": item["knowledge_type"],
            "authority": item["authority"],
            "status": item["status"],
            "source_id": item["source_id"],
            "source_url": item.get("source_url"),
            "score": round(score, 4),
        })
    return {
        "status": "ready" if evidence else "no_answer",
        "query": query,
        "evidence": evidence,
        "allowed_evidence_ids": [item["evidence_id"] for item in evidence],
        "index_version": index["index_version"],
        "answer_policy": "仅依据 evidence 回答；无证据时明确不知道；候选知识必须提示待用户确认。",
    }


def answer_question(query: str, *, top_k: int = 3) -> dict[str, Any]:
    """Create a conservative extractive answer; a validated LLM may replace this later."""
    retrieval = search_knowledge(query, top_k=top_k, minimum_score=0.20)
    if retrieval["status"] == "need_input":
        return {"schema_version": "1.0.0", "task": "illustration_domain_qa", "status": "blocked", "answer": "请先输入具体的插画行业问题。", "citations": [], "missing_information": ["用户问题"], "confirmation_required": False}
    if retrieval["status"] == "no_answer":
        return {"schema_version": "1.0.0", "task": "illustration_domain_qa", "status": "no_answer", "answer": "当前知识库没有找到足够证据，无法可靠回答。", "citations": [], "missing_information": ["与问题直接相关的已发布知识"], "confirmation_required": False}
    evidence = retrieval["evidence"]
    candidate = any(item["status"] in {"candidate_needs_user_confirmation", "needs_manual_review"} for item in evidence)
    answer = evidence[0]["text"]
    if candidate:
        answer += " 当前命中的部分知识仍待用户确认或人工核对，请不要把它当作正式平台结论。"
    return {
        "schema_version": "1.0.0",
        "task": "illustration_domain_qa",
        "status": "ready",
        "answer": answer,
        "citations": [item["evidence_id"] for item in evidence],
        "missing_information": [],
        "confirmation_required": candidate,
    }
