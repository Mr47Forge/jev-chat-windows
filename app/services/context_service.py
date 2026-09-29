# -*- coding: utf-8 -*-
"""会话分析上下文服务。

关键边界：
- judge_relationship 只给“当前场景判断”使用，不注入长期推测/攻略；
- relationship 给起草层使用，才允许带长期画像、备注、攻略和知识库。
"""
from __future__ import annotations

from app import chat_profiles, knowledge, persona_skill, relationship_memory
from app.services import strategy_service


def build(title: str, messages: list) -> dict:
    profile = chat_profiles.get(title)

    # 当前状态判断只能看到明确的会话关系标签 + 当前真实聊天。
    # 旧画像、关系趋势、策略建议不能反向污染“这轮到底发生了什么”。
    judge_relationship = str(profile.get("relationship") or "").strip() or "未设置"

    person_id = relationship_memory.resolve_person_id(title)
    person = relationship_memory.person_record(person_id)
    long_term = ""
    strategy = ""
    if person:
        long_term = relationship_memory.memory_context(person_id, include_intimacy=False)
        strategy = strategy_service.realtime_context(person_id, include_intimacy=False)

    # 起草层可以参考历史，但必须明确它不是本轮事实。
    relationship = judge_relationship
    notes = str(profile.get("notes") or "").strip()
    if notes:
        relationship += "\n联系人备注（历史参考，不是本轮新证据）：\n" + notes
    if long_term:
        relationship += "\n长期人物/关系背景（历史事实与推测，不能覆盖当前消息）：\n" + long_term
    if strategy:
        relationship += "\n互动策略参考（策略，不是对方事实）：\n" + strategy

    matched_notes = knowledge.match(title, messages)
    if matched_notes:
        relationship += "\n知识库背景（只把已有事实当事实，不要编造）：\n" + "\n".join(
            f"- {note['content']}" for note in matched_notes
        )

    persona_id = profile.get("persona_id", persona_skill.NO_PERSONA)
    persona_data = persona_skill.effective(persona_id)
    persona = persona_skill.prompt_text(persona_id)

    return {
        "profile": profile,
        "judge_relationship": judge_relationship,
        "relationship": relationship,
        "style": str(profile.get("style") or ""),
        "persona_id": persona_id,
        "persona": persona,
        "persona_name": persona_data.get("name") if persona_data else "",
        "knowledge_count": len(matched_notes),
        "person_id": person_id if person else "",
        "long_term_memory": bool(long_term),
        "interaction_strategy": bool(strategy),
    }
