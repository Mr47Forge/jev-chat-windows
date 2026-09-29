# -*- coding: utf-8 -*-
"""平台无关的人物资料入口。

微信只是其中一个来源。没有聊天记录时也可以直接创建人物、输入观察，
或者粘贴来自抖音/QQ/Telegram/其它平台的聊天给人物分析 Agent。
"""
from __future__ import annotations

from app import relationship_memory, settings
from core.persona import person_agent
from core.persona.module_policy import intimacy_allowed


def create_person(name: str, *, relationship: str = "未设置", person_id: str | None = None) -> dict:
    name = str(name or "").strip()
    if not name:
        raise ValueError("人物名称不能为空")
    pid = str(person_id or name).strip()
    relationship_memory.ensure_person(pid, display_name=name, relationship=relationship)
    return relationship_memory.person_record(pid)


def people() -> list[dict]:
    return relationship_memory.list_people()


def submit(
    person_id: str,
    text: str,
    *,
    source_kind: str = "observation",
    platform: str = "manual",
    relationship: str = "",
    allow_intimacy: bool | None = None,
) -> dict:
    if not settings.has_llm_key():
        raise ValueError("请先在全局设置中配置起草模型密钥")
    person = relationship_memory.person_record(person_id)
    effective_relationship = relationship or str(person.get("relationship") or "")
    return person_agent.analyze_input(
        person_id=person_id,
        text=text,
        source_kind=source_kind,
        platform=platform,
        provider=settings.draft_provider(),
        model=settings.draft_model() or "",
        base_url=settings.draft_base_url() or None,
        api_key=settings.llm_key(),
        thinking=settings.thinking(),
        relationship=effective_relationship,
        allow_intimacy=intimacy_allowed(effective_relationship, explicit=allow_intimacy),
    )


def dialogue(person_id: str, limit: int = 200) -> list[dict]:
    return relationship_memory.dialogue(person_id, limit=limit)
