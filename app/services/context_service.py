# -*- coding: utf-8 -*-
"""会话分析上下文服务：集中组装关系、备注、知识库和人格。

这个模块只负责“这轮分析应该带什么背景”，不负责调用模型，也不负责界面。
"""
from __future__ import annotations

from app import chat_profiles, knowledge, persona_skill, relationship_memory
from app.services import strategy_service


def build(title: str, messages: list) -> dict:
    """构造一轮分析所需的业务上下文。

    返回稳定字段：
    - profile: 当前会话资料
    - judge_relationship: 判断层只使用关系 + 联系人备注
    - relationship: 起草层使用关系 + 联系人备注 + 命中的知识库
    - style: 当前会话回复风格
    - persona_id / persona / persona_name: 人格选择和提示文本
    - knowledge_count: 本轮实际命中的知识库条数
    """
    profile = chat_profiles.get(title)

    judge_relationship = str(profile.get("relationship") or "").strip()
    notes = str(profile.get("notes") or "").strip()
    if notes:
        judge_relationship += "\n联系人备注：" + notes

    # 长期人物画像与关系趋势是平台无关的：可能来自微信、抖音、手工观察或其它来源。
    # 敏感亲密画像默认不进入普通实时聊天。
    person_id = relationship_memory.resolve_person_id(title)
    person = relationship_memory.person_record(person_id)
    long_term = ""
    strategy = ""
    if person:
        long_term = relationship_memory.memory_context(person_id, include_intimacy=False)
        strategy = strategy_service.realtime_context(person_id, include_intimacy=False)
        if long_term:
            judge_relationship += "\n长期人物/关系背景（事实与推测已区分）：\n" + long_term

    # 产品知识只给起草层。意图 / 危险度判断只需要关系和真实聊天，
    # 不应该被大量商品资料、规则文档挤占判断上下文。
    relationship = judge_relationship
    if strategy:
        relationship += "\n互动策略参考（不是对方事实）：\n" + strategy
    matched_notes = knowledge.match(title, messages)
    if matched_notes:
        relationship += "\n知识库背景（只把它当事实，不要编造）：\n" + "\n".join(
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
