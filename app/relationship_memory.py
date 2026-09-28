# -*- coding: utf-8 -*-
"""Jev 永久关系记忆库。

与 OCR、微信导入解耦：
- OCR 只负责当前聊天窗口；
- 微信历史导入负责首次/增量灌入真实历史；
- 本模块负责跨应用退出、电脑重启、程序升级长期保存人物画像和事件。

Windows 默认位置：
%LOCALAPPDATA%\\JevChat-Windows\\relationship_memory.db
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("JEV_DATA_DIR", "").strip()
    if override:
        root = Path(override)
    elif sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "JevChat-Windows"
    else:
        root = Path.home() / ".jev-chat-windows"
    root.mkdir(parents=True, exist_ok=True)
    return root


DB_PATH = data_dir() / "relationship_memory.db"


@contextmanager
def _db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    _init(con)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _init(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS people (
            person_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL DEFAULT '',
            relationship TEXT NOT NULL DEFAULT '恋爱对象',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            status TEXT NOT NULL DEFAULT 'active',
            source_type TEXT NOT NULL DEFAULT 'manual',
            source_id TEXT NOT NULL DEFAULT '',
            source_time INTEGER,
            evidence TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            UNIQUE(person_id, kind, content, source_id),
            FOREIGN KEY(person_id) REFERENCES people(person_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_memories_person_kind
        ON memories(person_id, kind, status);

        CREATE TABLE IF NOT EXISTS relationship_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            window_days INTEGER NOT NULL DEFAULT 30,
            stage TEXT NOT NULL DEFAULT '',
            trend TEXT NOT NULL DEFAULT '',
            initiative REAL,
            warmth REAL,
            conflict REAL,
            summary TEXT NOT NULL DEFAULT '',
            evidence TEXT NOT NULL DEFAULT '',
            observed_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(person_id) REFERENCES people(person_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_relationship_snapshots_person_time
        ON relationship_snapshots(person_id, observed_at DESC);

        CREATE TABLE IF NOT EXISTS memory_settings (
            person_id TEXT PRIMARY KEY,
            learning_enabled INTEGER NOT NULL DEFAULT 1,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(person_id) REFERENCES people(person_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS intimacy_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            dimension TEXT NOT NULL,
            value TEXT NOT NULL,
            scope TEXT NOT NULL,
            certainty TEXT NOT NULL DEFAULT 'explicit',
            confidence REAL NOT NULL DEFAULT 1.0,
            status TEXT NOT NULL DEFAULT 'active',
            source_type TEXT NOT NULL DEFAULT 'manual',
            source_id TEXT NOT NULL DEFAULT '',
            source_time INTEGER,
            evidence TEXT NOT NULL DEFAULT '',
            counterevidence TEXT NOT NULL DEFAULT '',
            valid_from INTEGER,
            valid_until INTEGER,
            supersedes_id INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            UNIQUE(person_id, dimension, value, scope, source_id),
            FOREIGN KEY(person_id) REFERENCES people(person_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_intimacy_preferences_person
        ON intimacy_preferences(person_id, status, dimension, scope);

        CREATE TABLE IF NOT EXISTS strategy_profiles (
            person_id TEXT PRIMARY KEY,
            schema TEXT NOT NULL DEFAULT 'jev-interaction-strategy/v1',
            payload TEXT NOT NULL DEFAULT '{}',
            source_type TEXT NOT NULL DEFAULT 'model',
            source_id TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(person_id) REFERENCES people(person_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS source_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'manual',
            author_role TEXT NOT NULL DEFAULT 'observer',
            content TEXT NOT NULL,
            external_id TEXT NOT NULL DEFAULT '',
            source_time INTEGER,
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at INTEGER NOT NULL,
            FOREIGN KEY(person_id) REFERENCES people(person_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_source_items_person_time
        ON source_items(person_id, created_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS analysis_dialogue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            source_item_id INTEGER,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(person_id) REFERENCES people(person_id) ON DELETE CASCADE,
            FOREIGN KEY(source_item_id) REFERENCES source_items(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_analysis_dialogue_person_time
        ON analysis_dialogue(person_id, created_at ASC, id ASC);

        CREATE TABLE IF NOT EXISTS import_state (
            person_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            cursor TEXT NOT NULL DEFAULT '',
            last_message_time INTEGER,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY(person_id, provider),
            FOREIGN KEY(person_id) REFERENCES people(person_id) ON DELETE CASCADE
        );
        """
    )
    # 兼容已经创建过的旧数据库：只补列，不清空用户记忆。
    cols = {row["name"] for row in con.execute("PRAGMA table_info(memories)").fetchall()}
    migrations = {
        "certainty": "TEXT NOT NULL DEFAULT 'explicit'",
        "valid_from": "INTEGER",
        "valid_until": "INTEGER",
        "supersedes_id": "INTEGER",
    }
    for name, ddl in migrations.items():
        if name not in cols:
            con.execute(f"ALTER TABLE memories ADD COLUMN {name} {ddl}")


def ensure_person(person_id: str, display_name: str = "", relationship: str | None = None) -> None:
    person_id = str(person_id or "").strip()
    if not person_id:
        raise ValueError("person_id 不能为空")
    now = int(time.time())
    relationship_explicit = relationship is not None and bool(str(relationship).strip())
    relationship_value = str(relationship).strip() if relationship_explicit else "恋爱对象"
    with _db() as con:
        con.execute(
            """INSERT INTO people(person_id, display_name, relationship, created_at, updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(person_id) DO UPDATE SET
                 display_name=CASE WHEN excluded.display_name<>'' THEN excluded.display_name ELSE people.display_name END,
                 relationship=CASE WHEN ? THEN excluded.relationship ELSE people.relationship END,
                 updated_at=excluded.updated_at""",
            (person_id, str(display_name or ""), relationship_value, now, now, 1 if relationship_explicit else 0),
        )


def list_people() -> list[dict]:
    """列出已经建立长期档案的人物，供平台无关的人物工作台使用。"""
    with _db() as con:
        return [dict(row) for row in con.execute(
            """SELECT person_id,display_name,relationship,created_at,updated_at
               FROM people ORDER BY updated_at DESC,created_at DESC"""
        ).fetchall()]


def person_record(person_id: str) -> dict:
    with _db() as con:
        row = con.execute(
            """SELECT person_id,display_name,relationship,created_at,updated_at
               FROM people WHERE person_id=?""",
            (str(person_id),),
        ).fetchone()
        return dict(row) if row else {}


def resolve_person_id(label: str) -> str:
    """界面会话名不是人物主键时，先按 display_name 反查。

    没找到就保留 label；这样手工人物、微信、抖音等来源可以逐步绑定到同一个人物。
    """
    label = str(label or "").strip()
    if not label:
        return ""
    with _db() as con:
        row = con.execute("SELECT person_id FROM people WHERE person_id=?", (label,)).fetchone()
        if row:
            return str(row["person_id"])
        row = con.execute(
            """SELECT person_id FROM people WHERE display_name=?
               ORDER BY updated_at DESC LIMIT 1""",
            (label,),
        ).fetchone()
        return str(row["person_id"]) if row else label


def add_source_item(
    person_id: str,
    content: str,
    *,
    source_kind: str = "observation",
    platform: str = "manual",
    author_role: str = "observer",
    external_id: str = "",
    source_time: int | None = None,
    metadata: dict | None = None,
) -> int:
    """保存平台无关的原始资料。

    原始资料和模型推断分开：这里保存“用户实际喂了什么”，后续画像只引用 source_item id。
    """
    person_id = str(person_id or "").strip()
    content = str(content or "").strip()
    if not person_id or not content:
        raise ValueError("person_id / content 不能为空")
    ensure_person(person_id)
    now = int(time.time())
    raw_meta = json.dumps(metadata or {}, ensure_ascii=False, separators=(",", ":"))
    with _db() as con:
        cur = con.execute(
            """INSERT INTO source_items
               (person_id,source_kind,platform,author_role,content,external_id,source_time,metadata,created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (person_id, str(source_kind), str(platform), str(author_role), content,
             str(external_id or ""), source_time, raw_meta, now),
        )
        return int(cur.lastrowid)


def source_items(person_id: str, limit: int = 5000) -> list[dict]:
    with _db() as con:
        rows = con.execute(
            """SELECT id,source_kind,platform,author_role,content,external_id,source_time,metadata,created_at
               FROM source_items WHERE person_id=?
               ORDER BY COALESCE(source_time,created_at) ASC,id ASC LIMIT ?""",
            (str(person_id), max(1, int(limit))),
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["metadata"] = json.loads(item.get("metadata") or "{}")
        except (TypeError, ValueError):
            item["metadata"] = {}
        out.append(item)
    return out


def add_dialogue_entry(
    person_id: str,
    role: str,
    content: str,
    *,
    source_item_id: int | None = None,
) -> int:
    person_id = str(person_id or "").strip()
    role = str(role or "").strip()
    content = str(content or "").strip()
    if not person_id or role not in {"user", "assistant"} or not content:
        raise ValueError("人物分析对话参数无效")
    ensure_person(person_id)
    with _db() as con:
        cur = con.execute(
            """INSERT INTO analysis_dialogue(person_id,role,content,source_item_id,created_at)
               VALUES(?,?,?,?,?)""",
            (person_id, role, content, source_item_id, int(time.time())),
        )
        return int(cur.lastrowid)


def dialogue(person_id: str, limit: int = 200) -> list[dict]:
    with _db() as con:
        return [dict(row) for row in con.execute(
            """SELECT id,role,content,source_item_id,created_at
               FROM analysis_dialogue WHERE person_id=?
               ORDER BY created_at ASC,id ASC LIMIT ?""",
            (str(person_id), max(1, int(limit))),
        ).fetchall()]


def save_strategy_profile(
    person_id: str,
    payload: dict,
    *,
    source_type: str = "model",
    source_id: str = "",
) -> dict:
    person_id = str(person_id or "").strip()
    if not person_id:
        raise ValueError("person_id 不能为空")
    if not isinstance(payload, dict):
        raise ValueError("payload 必须是对象")
    ensure_person(person_id)
    now = int(time.time())
    schema = str(payload.get("schema") or "jev-interaction-strategy/v1")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _db() as con:
        con.execute(
            """INSERT INTO strategy_profiles
               (person_id,schema,payload,source_type,source_id,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(person_id) DO UPDATE SET
                 schema=excluded.schema,
                 payload=excluded.payload,
                 source_type=excluded.source_type,
                 source_id=excluded.source_id,
                 updated_at=excluded.updated_at""",
            (person_id, schema, raw, str(source_type), str(source_id), now, now),
        )
    return load_strategy_profile(person_id)


def load_strategy_profile(person_id: str) -> dict:
    with _db() as con:
        row = con.execute(
            """SELECT schema,payload,source_type,source_id,created_at,updated_at
               FROM strategy_profiles WHERE person_id=?""",
            (str(person_id),),
        ).fetchone()
    if not row:
        return {}
    try:
        payload = json.loads(row["payload"])
    except (TypeError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload = dict(payload)
    payload["_storage"] = {
        "schema": row["schema"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    return payload


def all_memories(person_id: str, *, include_inactive: bool = True) -> list[dict]:
    sql = """SELECT id,kind,content,confidence,certainty,status,source_type,source_id,source_time,
                    evidence,valid_from,valid_until,supersedes_id,created_at,updated_at
             FROM memories WHERE person_id=?"""
    args: list = [str(person_id)]
    if not include_inactive:
        sql += " AND status='active'"
    sql += " ORDER BY COALESCE(source_time,updated_at) ASC,id ASC"
    with _db() as con:
        return [dict(row) for row in con.execute(sql, args).fetchall()]


def all_relationship_snapshots(person_id: str) -> list[dict]:
    with _db() as con:
        return [dict(row) for row in con.execute(
            """SELECT id,window_days,stage,trend,initiative,warmth,conflict,summary,evidence,
                      observed_at,created_at
               FROM relationship_snapshots WHERE person_id=?
               ORDER BY observed_at ASC,id ASC""",
            (str(person_id),),
        ).fetchall()]


def all_intimacy_preferences(person_id: str, *, include_inactive: bool = True) -> list[dict]:
    sql = """SELECT id,dimension,value,scope,certainty,confidence,status,source_type,source_id,
                    source_time,evidence,counterevidence,valid_from,valid_until,supersedes_id,
                    created_at,updated_at
             FROM intimacy_preferences WHERE person_id=?"""
    args: list = [str(person_id)]
    if not include_inactive:
        sql += " AND status='active'"
    sql += " ORDER BY COALESCE(source_time,updated_at) ASC,id ASC"
    with _db() as con:
        return [dict(row) for row in con.execute(sql, args).fetchall()]


def all_import_states(person_id: str) -> list[dict]:
    with _db() as con:
        return [dict(row) for row in con.execute(
            """SELECT provider,cursor,last_message_time,updated_at
               FROM import_state WHERE person_id=? ORDER BY provider""",
            (str(person_id),),
        ).fetchall()]


def remember(
    person_id: str,
    kind: str,
    content: str,
    *,
    confidence: float = 1.0,
    source_type: str = "manual",
    source_id: str = "",
    source_time: int | None = None,
    evidence: str = "",
    certainty: str = "explicit",
    valid_from: int | None = None,
    valid_until: int | None = None,
    supersedes_id: int | None = None,
) -> int:
    """保存一条长期记忆。kind 可用 like/dislike/boundary/habit/event/promise/profile 等。"""
    person_id, kind, content = map(lambda x: str(x or "").strip(), (person_id, kind, content))
    if not person_id or not kind or not content:
        raise ValueError("person_id / kind / content 不能为空")
    ensure_person(person_id)
    now = int(time.time())
    confidence = max(0.0, min(1.0, float(confidence)))
    certainty = str(certainty or "explicit").strip()
    if certainty not in {"explicit", "inferred", "strategy"}:
        raise ValueError("certainty 只能是 explicit / inferred / strategy")
    # 推测不得伪装成确定事实。
    if certainty == "inferred":
        confidence = min(confidence, 0.85)
    elif certainty == "strategy":
        confidence = min(confidence, 0.65)
    with _db() as con:
        con.execute(
            """INSERT INTO memories
               (person_id,kind,content,confidence,status,source_type,source_id,source_time,evidence,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(person_id,kind,content,source_id) DO UPDATE SET
                 confidence=excluded.confidence,
                 status='active',
                 source_type=excluded.source_type,
                 source_time=excluded.source_time,
                 evidence=excluded.evidence,
                 updated_at=excluded.updated_at""",
            (person_id, kind, content, confidence, "active", str(source_type), str(source_id),
             source_time, str(evidence or ""), now, now),
        )
        row = con.execute(
            "SELECT id FROM memories WHERE person_id=? AND kind=? AND content=? AND source_id=?",
            (person_id, kind, content, str(source_id)),
        ).fetchone()
        memory_id = int(row["id"])
        con.execute(
            """UPDATE memories SET certainty=?, valid_from=?, valid_until=?, supersedes_id=?
               WHERE id=?""",
            (certainty, valid_from if valid_from is not None else source_time,
             valid_until, supersedes_id, memory_id),
        )
        if supersedes_id is not None:
            con.execute(
                "UPDATE memories SET status='superseded', valid_until=?, updated_at=? WHERE id=? AND person_id=?",
                (valid_from if valid_from is not None else now, now, int(supersedes_id), person_id),
            )
        return memory_id


def recall(person_id: str, kinds: list[str] | None = None, limit: int = 100) -> list[dict]:
    now = int(time.time())
    sql = """SELECT id,kind,content,confidence,certainty,source_type,source_id,source_time,evidence,
                    valid_from,valid_until,supersedes_id,updated_at
             FROM memories
             WHERE person_id=? AND status='active'
               AND (valid_until IS NULL OR valid_until>?)"""
    args: list = [str(person_id), now]
    if kinds:
        marks = ",".join("?" for _ in kinds)
        sql += f" AND kind IN ({marks})"
        args.extend(str(x) for x in kinds)
    sql += " ORDER BY COALESCE(source_time,updated_at) DESC, id DESC LIMIT ?"
    args.append(max(1, int(limit)))
    with _db() as con:
        return [dict(row) for row in con.execute(sql, args).fetchall()]


def forget(memory_id: int) -> None:
    """软删除，避免分析器下一轮又把同一条旧结论立即写回来。"""
    with _db() as con:
        con.execute(
            "UPDATE memories SET status='revoked', updated_at=? WHERE id=?",
            (int(time.time()), int(memory_id)),
        )




def set_learning(person_id: str, enabled: bool) -> None:
    """暂停/恢复某个对象的自动记忆学习，不影响已有记忆读取。"""
    ensure_person(person_id)
    with _db() as con:
        con.execute(
            """INSERT INTO memory_settings(person_id,learning_enabled,updated_at) VALUES(?,?,?)
               ON CONFLICT(person_id) DO UPDATE SET
                 learning_enabled=excluded.learning_enabled, updated_at=excluded.updated_at""",
            (str(person_id), 1 if enabled else 0, int(time.time())),
        )


def learning_enabled(person_id: str) -> bool:
    with _db() as con:
        row = con.execute(
            "SELECT learning_enabled FROM memory_settings WHERE person_id=?", (str(person_id),)
        ).fetchone()
        return True if row is None else bool(row["learning_enabled"])


def add_relationship_snapshot(
    person_id: str, *, window_days: int = 30, stage: str = "", trend: str = "",
    initiative: float | None = None, warmth: float | None = None,
    conflict: float | None = None, summary: str = "", evidence: str = "",
    observed_at: int | None = None,
) -> int:
    """保存“我们之间”的阶段/趋势；与“她是什么样的人”分开。"""
    ensure_person(person_id)
    now = int(time.time())
    with _db() as con:
        cur = con.execute(
            """INSERT INTO relationship_snapshots
               (person_id,window_days,stage,trend,initiative,warmth,conflict,summary,evidence,observed_at,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (str(person_id), max(1, int(window_days)), str(stage), str(trend),
             initiative, warmth, conflict, str(summary), str(evidence),
             int(observed_at or now), now),
        )
        return int(cur.lastrowid)


def relationship_trend(person_id: str, limit: int = 6) -> list[dict]:
    """返回最近多个时间窗口，供 Jev 判断升温/降温，而不是被很久以前的状态绑死。"""
    with _db() as con:
        return [dict(row) for row in con.execute(
            """SELECT id,window_days,stage,trend,initiative,warmth,conflict,summary,evidence,observed_at
               FROM relationship_snapshots WHERE person_id=?
               ORDER BY observed_at DESC,id DESC LIMIT ?""",
            (str(person_id), max(1, int(limit))),
        ).fetchall()]


def relationship_context(person_id: str, limit: int = 4) -> str:
    rows = relationship_trend(person_id, limit)
    if not rows:
        return ""
    lines = ["【我们的关系趋势】"]
    for row in reversed(rows):
        bits = [f"{row['window_days']}天窗口"]
        if row["stage"]:
            bits.append("阶段=" + row["stage"])
        if row["trend"]:
            bits.append("趋势=" + row["trend"])
        if row["summary"]:
            bits.append(row["summary"])
        lines.append("- " + "；".join(bits))
    return "\n".join(lines)


def memory_context(person_id: str, *, include_intimacy: bool = False) -> str:
    """统一提供给 Jev/狗头军师：人物画像 + 关系趋势。

    敏感亲密画像默认不注入；只有当前话题确实相关时才显式 include_intimacy=True。
    """
    parts = [profile_context(person_id), relationship_context(person_id)]
    if include_intimacy:
        parts.append(intimacy_context(person_id))
    return "\n\n".join(x for x in parts if x).strip()



_INTIMACY_SCOPES = {
    "topic_interest", "fantasy", "real_world_willingness", "experience", "boundary",
}
_INTIMACY_CERTAINTY = {"explicit", "inferred"}
_INTIMACY_SCOPE_LABELS = {
    "topic_interest": "话题兴趣",
    "fantasy": "幻想偏好",
    "real_world_willingness": "现实意愿",
    "experience": "实际经历",
    "boundary": "明确边界",
}


def add_intimacy_preference(
    person_id: str,
    dimension: str,
    value: str,
    *,
    scope: str = "topic_interest",
    certainty: str = "explicit",
    confidence: float = 1.0,
    source_type: str = "manual",
    source_id: str = "",
    source_time: int | None = None,
    evidence: str = "",
    counterevidence: str = "",
    valid_from: int | None = None,
    valid_until: int | None = None,
    supersedes_id: int | None = None,
) -> int:
    """保存敏感的亲密/性偏好画像。

    scope 必须区分“聊得来/幻想”与“现实愿意/实际经历/边界”。
    inferred 永远只是推测，不能当作现实同意；越接近现实行为，推测置信度上限越低。
    """
    person_id = str(person_id or "").strip()
    dimension = str(dimension or "").strip()
    value = str(value or "").strip()
    scope = str(scope or "").strip()
    certainty = str(certainty or "").strip()
    if not person_id or not dimension or not value:
        raise ValueError("person_id / dimension / value 不能为空")
    if scope not in _INTIMACY_SCOPES:
        raise ValueError("scope 无效")
    if certainty not in _INTIMACY_CERTAINTY:
        raise ValueError("certainty 只能是 explicit / inferred")

    ensure_person(person_id)
    now = int(time.time())
    confidence = max(0.0, min(1.0, float(confidence)))
    if certainty == "inferred":
        # 敏感画像比普通人物画像更保守。
        confidence = min(confidence, 0.75)
        if scope in {"real_world_willingness", "experience", "boundary"}:
            confidence = min(confidence, 0.60)

    with _db() as con:
        con.execute(
            """INSERT INTO intimacy_preferences
               (person_id,dimension,value,scope,certainty,confidence,status,
                source_type,source_id,source_time,evidence,counterevidence,
                valid_from,valid_until,supersedes_id,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(person_id,dimension,value,scope,source_id) DO UPDATE SET
                 certainty=excluded.certainty,
                 confidence=excluded.confidence,
                 status='active',
                 source_type=excluded.source_type,
                 source_time=excluded.source_time,
                 evidence=excluded.evidence,
                 counterevidence=excluded.counterevidence,
                 valid_from=excluded.valid_from,
                 valid_until=excluded.valid_until,
                 supersedes_id=excluded.supersedes_id,
                 updated_at=excluded.updated_at""",
            (person_id, dimension, value, scope, certainty, confidence, "active",
             str(source_type), str(source_id), source_time, str(evidence or ""),
             str(counterevidence or ""), valid_from if valid_from is not None else source_time,
             valid_until, supersedes_id, now, now),
        )
        row = con.execute(
            """SELECT id FROM intimacy_preferences
               WHERE person_id=? AND dimension=? AND value=? AND scope=? AND source_id=?""",
            (person_id, dimension, value, scope, str(source_id)),
        ).fetchone()
        preference_id = int(row["id"])
        if supersedes_id is not None:
            con.execute(
                """UPDATE intimacy_preferences
                   SET status='superseded', valid_until=?, updated_at=?
                   WHERE id=? AND person_id=?""",
                (valid_from if valid_from is not None else now, now, int(supersedes_id), person_id),
            )
        return preference_id


def recall_intimacy_preferences(
    person_id: str,
    *,
    scopes: list[str] | None = None,
    min_confidence: float = 0.0,
    limit: int = 100,
) -> list[dict]:
    """读取敏感画像；调用方必须主动调用，本模块不会把它默认塞进每轮聊天。"""
    now = int(time.time())
    sql = """SELECT id,dimension,value,scope,certainty,confidence,source_type,source_id,
                    source_time,evidence,counterevidence,valid_from,valid_until,supersedes_id,updated_at
             FROM intimacy_preferences
             WHERE person_id=? AND status='active'
               AND confidence>=?
               AND (valid_until IS NULL OR valid_until>?)"""
    args: list = [str(person_id), max(0.0, min(1.0, float(min_confidence))), now]
    if scopes:
        clean = [str(x) for x in scopes if str(x) in _INTIMACY_SCOPES]
        if not clean:
            return []
        sql += " AND scope IN (" + ",".join("?" for _ in clean) + ")"
        args.extend(clean)
    sql += " ORDER BY COALESCE(source_time,updated_at) DESC,id DESC LIMIT ?"
    args.append(max(1, int(limit)))
    with _db() as con:
        return [dict(row) for row in con.execute(sql, args).fetchall()]


def revoke_intimacy_preference(preference_id: int) -> None:
    with _db() as con:
        con.execute(
            "UPDATE intimacy_preferences SET status='revoked', updated_at=? WHERE id=?",
            (int(time.time()), int(preference_id)),
        )


def intimacy_context(person_id: str, limit: int = 40) -> str:
    """仅供亲密/性相关场景显式调用。

    “幻想/话题兴趣”不会被表述成“现实愿意”；推测也永远带推测标记。
    """
    rows = recall_intimacy_preferences(person_id, limit=limit)
    if not rows:
        return ""
    grouped: dict[str, list[str]] = {}
    for row in reversed(rows):
        scope = _INTIMACY_SCOPE_LABELS.get(row["scope"], row["scope"])
        if row["certainty"] == "inferred":
            prefix = f"（推测 {round(float(row['confidence']) * 100)}%）"
        else:
            prefix = "（明确）"
        grouped.setdefault(scope, []).append(
            f"{prefix}{row['dimension']}：{row['value']}"
        )
    head = [
        "【亲密与性偏好】",
        "注意：话题兴趣/幻想不等于现实意愿；任何现实行为都以当下明确同意和边界为准。",
    ]
    for scope, values in grouped.items():
        head.append(f"【{scope}】")
        head.extend("- " + x for x in values)
    return "\n".join(head)


def set_import_state(person_id: str, provider: str, cursor: str = "",
                     last_message_time: int | None = None) -> None:
    ensure_person(person_id)
    with _db() as con:
        con.execute(
            """INSERT INTO import_state(person_id,provider,cursor,last_message_time,updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(person_id,provider) DO UPDATE SET
                 cursor=excluded.cursor,
                 last_message_time=excluded.last_message_time,
                 updated_at=excluded.updated_at""",
            (str(person_id), str(provider), str(cursor or ""), last_message_time, int(time.time())),
        )


def get_import_state(person_id: str, provider: str) -> dict:
    with _db() as con:
        row = con.execute(
            "SELECT cursor,last_message_time,updated_at FROM import_state WHERE person_id=? AND provider=?",
            (str(person_id), str(provider)),
        ).fetchone()
        return dict(row) if row else {}


def profile_context(person_id: str, limit: int = 60) -> str:
    """生成给 Jev/狗头军师使用的精简持久记忆文本。"""
    rows = recall(person_id, limit=limit)
    if not rows:
        return ""
    labels = {
        "like": "喜欢", "dislike": "讨厌", "boundary": "边界/雷区",
        "habit": "习惯", "event": "重要事件", "promise": "约定",
        "profile": "人物特征", "communication": "沟通偏好",
    }
    grouped: dict[str, list[str]] = {}
    for row in reversed(rows):
        prefix = {"explicit": "", "inferred": "（推测）", "strategy": "（策略判断）"}.get(row.get("certainty"), "")
        grouped.setdefault(labels.get(row["kind"], row["kind"]), []).append(prefix + row["content"])
    return "\n".join(
        f"【{kind}】\n" + "\n".join(f"- {x}" for x in values)
        for kind, values in grouped.items()
    )


if __name__ == "__main__":
    # 独立烟雾测试：写入 -> 关闭连接 -> 重新读取，验证不是内存变量。
    ensure_person("__selftest__", "测试对象")
    mid = remember("__selftest__", "like", "测试持久记忆", source_type="selftest", source_id="1")
    assert any(x["id"] == mid for x in recall("__selftest__"))
    print("relationship_memory ok:", DB_PATH)
