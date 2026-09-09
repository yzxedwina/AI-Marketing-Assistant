"""Build a deterministic local keyword index from approved knowledge files."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.rag import KB_DIR, _tokens

DATASETS = {
    "industry_terms.json": "industry_term",
    "platform_rules.json": "platform_rule",
    "reference_cases.json": "reference_case",
}
AUTHORITY_RANK = {
    "official": 100,
    "official_page_registered_content_unverified": 60,
    "user_confirmed_for_own_business": 80,
    "candidate_needs_user_confirmation": 40,
}


def main() -> None:
    registry = json.loads((KB_DIR / "source_registry.json").read_text(encoding="utf-8"))
    source_map = {item["source_id"]: item for item in registry["sources"]}
    chunks = []
    for filename, knowledge_type in DATASETS.items():
        dataset = json.loads((KB_DIR / filename).read_text(encoding="utf-8"))
        for record in dataset["records"]:
            source = source_map[record["source_id"]]
            title = record.get("term") or record.get("title")
            text = record.get("definition") or record.get("content")
            aliases = record.get("aliases", [])
            searchable = " ".join([title, *aliases, text, record.get("category", ""), record.get("platform", "")])
            authority = record.get("authority") or source["authority"]
            chunks.append({
                "knowledge_id": record["knowledge_id"],
                "knowledge_type": knowledge_type,
                "title": title,
                "aliases": aliases,
                "text": text,
                "searchable_text": searchable,
                "tokens": _tokens(searchable),
                "platform": record.get("platform"),
                "authority": authority,
                "authority_rank": AUTHORITY_RANK.get(authority, 50),
                "status": record["status"],
                "source_id": record["source_id"],
                "source_url": source.get("url"),
            })
    chunks.sort(key=lambda item: item["knowledge_id"])
    output = {"index_version": "rag-keyword-v1.0.0", "built_from_registry": registry["registry_version"], "chunks": chunks}
    target = KB_DIR / "index" / "chunks.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"built {len(chunks)} chunks -> {target}")


if __name__ == "__main__":
    main()
