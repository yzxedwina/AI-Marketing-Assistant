"""Seed local long-term memory with the confirmed demo profile and preferences."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.memory import MemoryStore, PreferenceInput


USER_ID = "USR-EDWINA-001"


def main() -> None:
    profile = json.loads((ROOT / "data" / "profile_edwinayyy_candidate.json").read_text(encoding="utf-8"))
    store = MemoryStore()
    store.save_confirmed_profile(USER_ID, profile)
    preferences = [
        PreferenceInput(key="preferred_medium", value="traditional"),
        PreferenceInput(key="preferred_subjects", value=["宠物", "兽设"]),
        PreferenceInput(key="preferred_styles", value=["水彩", "平涂"]),
        PreferenceInput(key="accepted_services", value=["带场景手绘插图", "动物大头挂件"]),
        PreferenceInput(key="excluded_business", value=["电子插画", "写实人像"]),
        PreferenceInput(key="primary_marketing_platform", value="xiaohongshu"),
    ]
    for preference in preferences:
        store.save_preference(USER_ID, preference)
    context = store.load_context(USER_ID)
    print(json.dumps({
        "user_id": USER_ID,
        "has_memory": context["has_memory"],
        "profile_status": context["confirmed_profile"]["profile_status"],
        "preference_count": len(context["confirmed_preferences"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
