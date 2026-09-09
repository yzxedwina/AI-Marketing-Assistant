"""Deterministic local long-term memory for the MVP.

Memory is deliberately separated into confirmed profile facts, confirmed user
preferences, and append-only historical records. Temporary trends and raw LLM
inferences must not be stored as stable facts.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.profile import UserProfile


DEFAULT_DB_PATH = Path(os.getenv(
    "DATABASE_PATH",
    str(Path(__file__).resolve().parents[1] / "data" / "memory.sqlite3"),
))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=100)
    value: Any
    source: Literal["user_confirmed", "user_edited"] = "user_confirmed"


class AnalysisRecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis_type: Literal["opportunity", "marketing_plan", "content_plan"]
    result_id: str = Field(min_length=1, max_length=100)
    result: Dict[str, Any]
    created_at: Optional[str] = None


class OutcomeRecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    direction: str = Field(min_length=1, max_length=200)
    platform: Literal["xiaohongshu", "huajia", "cross_platform"]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    capacity_status: Optional[Literal["available", "near_limit", "full", "unknown"]] = "unknown"
    source: Literal["user_reported", "authorized_platform"]
    observed_at: str
    note: Optional[str] = Field(default=None, max_length=500)


class MemoryStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profile_memory (
                    user_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS preference_memory (
                    user_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, preference_key)
                );
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    result_id TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (user_id, analysis_type, result_id)
                );
                CREATE TABLE IF NOT EXISTS outcome_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    capacity_status TEXT,
                    source TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    note TEXT,
                    recorded_at TEXT NOT NULL
                );
                """
            )

    def save_confirmed_profile(self, user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        parsed = UserProfile.model_validate(profile)
        if parsed.profile_status != "confirmed":
            raise ValueError("只有用户已确认画像可以写入长期 Memory")
        timestamp = utc_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO profile_memory(user_id, profile_id, profile_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_id=excluded.profile_id,
                    profile_json=excluded.profile_json,
                    updated_at=excluded.updated_at""",
                (user_id, parsed.profile_id, json.dumps(parsed.model_dump(), ensure_ascii=False), timestamp),
            )
        return {"user_id": user_id, "profile_id": parsed.profile_id, "updated_at": timestamp}

    def save_preference(self, user_id: str, preference: PreferenceInput) -> Dict[str, Any]:
        timestamp = utc_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO preference_memory(user_id, preference_key, value_json, source, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, preference_key) DO UPDATE SET
                    value_json=excluded.value_json,
                    source=excluded.source,
                    updated_at=excluded.updated_at""",
                (user_id, preference.key, json.dumps(preference.value, ensure_ascii=False), preference.source, timestamp),
            )
        return {"key": preference.key, "value": preference.value, "source": preference.source, "updated_at": timestamp}

    def add_analysis(self, user_id: str, record: AnalysisRecordInput) -> Dict[str, Any]:
        created_at = record.created_at or utc_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO analysis_history(user_id, analysis_type, result_id, result_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, analysis_type, result_id) DO UPDATE SET
                    result_json=excluded.result_json, created_at=excluded.created_at""",
                (user_id, record.analysis_type, record.result_id, json.dumps(record.result, ensure_ascii=False), created_at),
            )
        return {"analysis_type": record.analysis_type, "result_id": record.result_id, "created_at": created_at}

    def add_outcome(self, user_id: str, record: OutcomeRecordInput) -> Dict[str, Any]:
        recorded_at = utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO outcome_history(
                    user_id, direction, platform, metrics_json, capacity_status,
                    source, observed_at, note, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id, record.direction, record.platform,
                    json.dumps(record.metrics, ensure_ascii=False), record.capacity_status,
                    record.source, record.observed_at, record.note, recorded_at,
                ),
            )
        return {"outcome_id": cursor.lastrowid, "recorded_at": recorded_at}

    def load_context(self, user_id: str, history_limit: int = 10) -> Dict[str, Any]:
        with self._connect() as connection:
            profile_row = connection.execute(
                "SELECT profile_json, updated_at FROM profile_memory WHERE user_id=?", (user_id,)
            ).fetchone()
            preference_rows = connection.execute(
                """SELECT preference_key, value_json, source, updated_at
                FROM preference_memory WHERE user_id=? ORDER BY preference_key""", (user_id,)
            ).fetchall()
            analysis_rows = connection.execute(
                """SELECT analysis_type, result_id, result_json, created_at
                FROM analysis_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?""",
                (user_id, history_limit),
            ).fetchall()
            outcome_rows = connection.execute(
                """SELECT id, direction, platform, metrics_json, capacity_status, source,
                observed_at, note, recorded_at FROM outcome_history
                WHERE user_id=? ORDER BY observed_at DESC, id DESC LIMIT ?""",
                (user_id, history_limit),
            ).fetchall()

        return {
            "user_id": user_id,
            "has_memory": bool(profile_row or preference_rows or analysis_rows or outcome_rows),
            "confirmed_profile": json.loads(profile_row["profile_json"]) if profile_row else None,
            "profile_updated_at": profile_row["updated_at"] if profile_row else None,
            "confirmed_preferences": [
                {"key": row["preference_key"], "value": json.loads(row["value_json"]), "source": row["source"], "updated_at": row["updated_at"]}
                for row in preference_rows
            ],
            "analysis_history": [
                {"analysis_type": row["analysis_type"], "result_id": row["result_id"], "result": json.loads(row["result_json"]), "created_at": row["created_at"]}
                for row in analysis_rows
            ],
            "outcome_history": [
                {"outcome_id": row["id"], "direction": row["direction"], "platform": row["platform"], "metrics": json.loads(row["metrics_json"]), "capacity_status": row["capacity_status"], "source": row["source"], "observed_at": row["observed_at"], "note": row["note"], "recorded_at": row["recorded_at"]}
                for row in outcome_rows
            ],
        }


memory_store = MemoryStore()
