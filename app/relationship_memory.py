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


def memory_context(person_id: str) -> str:
    """统一提供给 Jev/狗头军师：人物画像 + 我们的关系趋势。"""
    parts = [profile_context(person_id), relationship_context(person_id)]
    return "\n\n".join(x for x in parts if x).strip()


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
