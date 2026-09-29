# -*- coding: utf-8 -*-
"""人物资料 Markdown 导出。

导出范围：人物事实/推测、关系趋势、亲密偏好、互动攻略、原始资料、
人物分析 Agent 对话、导入状态，以及同名本地聊天历史。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app import chat_history, chat_profiles, relationship_memory


def _dt(value) -> str:
    try:
        if value is None:
            return ""
        return datetime.fromtimestamp(int(value)).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return str(value or "")


def _esc(value) -> str:
    return str(value or "").replace("\r", "").strip()


def _bullet(text: str, indent: int = 0) -> str:
    return " " * indent + "- " + _esc(text)


def _strategy_md(strategy: dict) -> list[str]:
    if not strategy:
        return ["暂无已生成的互动攻略。"]
    s = {k: v for k, v in strategy.items() if k != "_storage"}
    lines = []
    if s.get("summary"):
        lines += ["**总体策略：** " + _esc(s["summary"]), ""]

    praise = s.get("praise") or {}
    lines.append("### 夸奖方式")
    targets = praise.get("best_targets") or []
    if not targets:
        lines.append("- 暂无")
    for x in targets:
        if not isinstance(x, dict):
            continue
        try:
            conf = round(float(x.get("confidence") or 0) * 100)
        except (TypeError, ValueError):
            conf = 0
        lines.append(_bullet(f"{x.get('target','')}｜置信度 {conf}%"))
        if x.get("why"):
            lines.append(_bullet("为什么：" + _esc(x["why"]), 2))
        if x.get("how"):
            lines.append(_bullet("怎么夸：" + _esc(x["how"]), 2))
        if x.get("example"):
            lines.append(_bullet("示例：" + _esc(x["example"]), 2))
        for ev in x.get("evidence") or []:
            lines.append(_bullet("证据：" + _esc(ev), 4))
    for x in praise.get("avoid") or []:
        if isinstance(x, dict):
            lines.append(_bullet(
                "少用：" + _esc(x.get("item")) +
                ("｜" + _esc(x.get("why")) if x.get("why") else "")
            ))

    conv = s.get("conversation") or {}
    lines += ["", "### 聊天方式"]
    for x in conv.get("works") or []:
        if isinstance(x, dict):
            lines.append(_bullet(
                _esc(x.get("item")) +
                ("｜" + _esc(x.get("how")) if x.get("how") else "")
            ))
    for x in conv.get("avoid") or []:
        if isinstance(x, dict):
            lines.append(_bullet(
                "少用：" + _esc(x.get("item")) +
                ("｜" + _esc(x.get("why")) if x.get("why") else "")
            ))
    if not (conv.get("works") or conv.get("avoid")):
        lines.append("- 暂无")

    support = s.get("emotional_support") or {}
    lines += ["", "### 情绪安抚"]
    if support.get("preferred"):
        lines.append(_bullet("优先方式：" + _esc(support["preferred"])))
    for step in support.get("steps") or []:
        lines.append(_bullet(_esc(step)))
    for item in support.get("avoid") or []:
        lines.append(_bullet("避免：" + _esc(item)))
    if not support:
        lines.append("- 暂无")

    progress = s.get("relationship_progression") or {}
    lines += ["", "### 关系推进"]
    lines.append(_bullet("当前阶段：" + _esc(progress.get("current_stage") or "未知")))
    if progress.get("next_step"):
        lines.append(_bullet("下一步：" + _esc(progress["next_step"])))
    for x in progress.get("examples") or []:
        lines.append(_bullet("表达骨架：" + _esc(x)))
    for x in progress.get("advance_signals") or []:
        lines.append(_bullet("可继续信号：" + _esc(x)))
    for x in progress.get("pause_signals") or []:
        lines.append(_bullet("暂缓信号：" + _esc(x)))
    for x in progress.get("stop_signals") or []:
        lines.append(_bullet("停止信号：" + _esc(x)))

    intimacy = s.get("intimacy_progression") or {}
    lines += ["", "### 亲密话题深度建议（不是关系阶段）"]
    if intimacy:
        lines.append(_bullet(
            f"当前：{intimacy.get('current_level',0)}级 {_esc(intimacy.get('current_name'))}"
        ))
        lines.append(_bullet(
            f"当前可承接：{intimacy.get('next_level',0)}级 {_esc(intimacy.get('next_name'))}"
        ))
        for x in intimacy.get("recommended_topics") or []:
            lines.append(_bullet("当前可聊：" + _esc(x)))
        for x in intimacy.get("transition_examples") or []:
            lines.append(_bullet("过渡表达：" + _esc(x)))
        for x in intimacy.get("do_not_jump_to") or []:
            lines.append(_bullet("暂不要跳到：" + _esc(x)))
        for x in intimacy.get("advance_signals") or []:
            lines.append(_bullet("可继续信号：" + _esc(x)))
        for x in intimacy.get("pause_signals") or []:
            lines.append(_bullet("暂缓信号：" + _esc(x)))
        for x in intimacy.get("stop_signals") or []:
            lines.append(_bullet("停止信号：" + _esc(x)))
    else:
        lines.append("- 暂无")

    risks = s.get("boundaries_and_risks") or []
    lines += ["", "### 边界与风险"]
    if not risks:
        lines.append("- 暂无")
    for x in risks:
        if isinstance(x, dict):
            lines.append(_bullet(
                _esc(x.get("item")) +
                ("｜处理：" + _esc(x.get("action")) if x.get("action") else "")
            ))

    unknowns = s.get("unknowns") or []
    lines += ["", "### 仍未知"]
    if not unknowns:
        lines.append("- 暂无")
    for x in unknowns:
        lines.append(_bullet(_esc(x)))
    return lines


def build_person_markdown(person_id: str) -> str:
    person_id = relationship_memory.resolve_person_id(person_id)
    person = relationship_memory.person_record(person_id)
    if not person:
        raise ValueError("人物不存在")

    name = person.get("display_name") or person_id
    lines = [
        f"# {name} · Jev 人物完整档案",
        "",
        f"- 人物 ID：{person_id}",
        f"- 关系：{_esc(person.get('relationship'))}",
        f"- 建档时间：{_dt(person.get('created_at'))}",
        f"- 最近更新：{_dt(person.get('updated_at'))}",
        f"- 导出时间：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "> 本文件同时包含明确事实、模型推测和策略建议。推测/策略不等于事实；亲密幻想不等于现实意愿。",
        "",
    ]

    profile = chat_profiles.get(str(name))
    if profile.get("saved"):
        lines += [
            "## 会话设置",
            "",
            _bullet("会话类型：" + _esc(profile.get("chat_type"))),
            _bullet("回复风格：" + _esc(profile.get("style"))),
            _bullet("备注：" + (_esc(profile.get("notes")) or "无")),
            _bullet("别名：" + ("、".join(profile.get("aliases") or []) or "无")),
            _bullet("人格 Skill：" + _esc(profile.get("persona_id"))),
            "",
        ]

    lines += ["## 人物长期记忆", ""]
    memories = relationship_memory.all_memories(person_id, include_inactive=True)
    if not memories:
        lines.append("- 暂无")
    for row in memories:
        try:
            conf = round(float(row.get("confidence") or 0) * 100)
        except (TypeError, ValueError):
            conf = 0
        lines.append(_bullet(
            f"[{row.get('status')}] [{row.get('certainty')}] "
            f"{row.get('kind')}：{_esc(row.get('content'))} （置信度 {conf}%）"
        ))
        if row.get("evidence"):
            lines.append(_bullet("证据：" + _esc(row["evidence"]), 2))
        lines.append(_bullet(
            f"来源：{row.get('source_type')} / {row.get('source_id')}；"
            f"时间：{_dt(row.get('source_time') or row.get('updated_at'))}",
            2,
        ))

    lines += ["", "## 关系趋势", ""]
    snapshots = relationship_memory.all_relationship_snapshots(person_id)
    if not snapshots:
        lines.append("- 暂无")
    for row in snapshots:
        parts = [
            f"{row.get('window_days')}天窗口",
            "阶段=" + _esc(row.get("stage")) if row.get("stage") else "",
            "趋势=" + _esc(row.get("trend")) if row.get("trend") else "",
            _esc(row.get("summary")),
        ]
        lines.append(_bullet("；".join(x for x in parts if x)))
        if row.get("evidence"):
            lines.append(_bullet("证据：" + _esc(row["evidence"]), 2))
        lines.append(_bullet("观察时间：" + _dt(row.get("observed_at")), 2))

    lines += ["", "## 亲密与性偏好画像", ""]
    intimate = relationship_memory.all_intimacy_preferences(person_id, include_inactive=True)
    if not intimate:
        lines.append("- 暂无")
    for row in intimate:
        try:
            conf = round(float(row.get("confidence") or 0) * 100)
        except (TypeError, ValueError):
            conf = 0
        lines.append(_bullet(
            f"[{row.get('status')}] [{row.get('certainty')}] [{row.get('scope')}] "
            f"{_esc(row.get('dimension'))}：{_esc(row.get('value'))} （置信度 {conf}%）"
        ))
        if row.get("evidence"):
            lines.append(_bullet("证据：" + _esc(row["evidence"]), 2))
        if row.get("counterevidence"):
            lines.append(_bullet("反证：" + _esc(row["counterevidence"]), 2))
    lines += [
        "",
        "> 话题兴趣 / 幻想 / 现实意愿 / 实际经历 / 明确边界是不同层级，不能互相自动升级。",
        "",
        "## 互动攻略",
        "",
    ]
    lines += _strategy_md(relationship_memory.load_strategy_profile(person_id))

    lines += ["", "## 原始资料来源", ""]
    sources = relationship_memory.source_items(person_id)
    if not sources:
        lines.append("- 暂无")
    for row in sources:
        lines += [
            f"### 资料 #{row['id']} · {row.get('platform')} / {row.get('source_kind')}",
            "",
            f"- 记录时间：{_dt(row.get('source_time') or row.get('created_at'))}",
            f"- 作者角色：{_esc(row.get('author_role'))}",
            "",
            _esc(row.get("content")),
            "",
        ]
        if row.get("metadata"):
            lines += ["元数据：", "", json.dumps(row["metadata"], ensure_ascii=False, indent=2), ""]

    lines += ["## 人物分析 Agent 对话", ""]
    dialogue = relationship_memory.dialogue(person_id, limit=10000)
    if not dialogue:
        lines.append("- 暂无")
    for row in dialogue:
        who = "我" if row.get("role") == "user" else "分析 Agent"
        lines += [
            f"### {who} · {_dt(row.get('created_at'))}",
            "",
            _esc(row.get("content")),
            "",
        ]

    lines += ["## 外部导入状态", ""]
    states = relationship_memory.all_import_states(person_id)
    if not states:
        lines.append("- 暂无")
    for row in states:
        lines.append(_bullet(
            f"{row.get('provider')}：cursor={row.get('cursor') or '无'}；"
            f"最后消息={_dt(row.get('last_message_time'))}；"
            f"更新时间={_dt(row.get('updated_at'))}"
        ))

    local = chat_history.load(str(name), limit=100000)
    lines += ["", "## 本地实时聊天历史", ""]
    if not local:
        lines.append("- 暂无或本地历史记录未开启。")
    for who, text, speaker in local:
        label = "我" if who == "me" else (speaker or str(name))
        lines.append(f"- **{label}：** {_esc(text)}")

    return "\n".join(lines).rstrip() + "\n"


def export_person_markdown(person_id: str, path: str | Path) -> Path:
    path = Path(path)
    if path.suffix.lower() != ".md":
        path = path.with_suffix(".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_person_markdown(person_id), encoding="utf-8")
    return path


def build_all_people_markdown() -> str:
    people = relationship_memory.list_people()
    if not people:
        return "# Jev 人物档案\n\n暂无人物。\n"
    chunks = ["# Jev 全部人物档案", ""]
    for index, person in enumerate(people):
        if index:
            chunks += ["", "---", ""]
        chunks.append(build_person_markdown(person["person_id"]))
    return "\n".join(chunks)


def export_all_people_markdown(path: str | Path) -> Path:
    path = Path(path)
    if path.suffix.lower() != ".md":
        path = path.with_suffix(".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_all_people_markdown(), encoding="utf-8")
    return path
