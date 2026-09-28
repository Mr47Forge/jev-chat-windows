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


def ensure_person(person_id: str, display_name: str = "", relationship: str = "恋爱对象") -> None:
    person_id = str(person_id or "").strip()
    if not person_id:
        raise ValueError("person_id 不能为空")
    now = int(time.time())
    with _db() as con:
        con.execute(
            """INSERT INTO people(person_id, display_name, relationship, created_at, updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(person_id) DO UPDATE SET
                 display_name=CASE WHEN excluded.display_name<>'' THEN excluded.display_name ELSE people.display_name END,
                 relationship=excluded.relationship,
                 updated_at=excluded.updated_at""",
            (person_id, str(display_name or ""), str(relationship or "恋爱对象"), now, now),
        )


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
) -> int:
    """保存一条长期记忆。kind 可用 like/dislike/boundary/habit/event/promise/profile 等。"""
    person_id, kind, content = map(lambda x: str(x or "").strip(), (person_id, kind, content))
    if not person_id or not kind or not content:
        raise ValueError("person_id / kind / content 不能为空")
    ensure_person(person_id)
    now = int(time.time())
    confidence = max(0.0, min(1.0, float(confidence)))
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
        return int(row["id"])


def recall(person_id: str, kinds: list[str] | None = None, limit: int = 100) -> list[dict]:
    sql = """SELECT id,kind,content,confidence,source_type,source_id,source_time,evidence,updated_at
             FROM memories WHERE person_id=? AND status='active'"""
    args: list = [str(person_id)]
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
        grouped.setdefault(labels.get(row["kind"], row["kind"]), []).append(row["content"])
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
