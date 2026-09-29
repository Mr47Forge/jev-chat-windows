# -*- coding: utf-8 -*-
"""人物互动攻略服务：平台无关。"""
from __future__ import annotations

from app import chat_profiles, relationship_memory, settings
from core.persona import interaction_strategy
from core.persona.module_policy import intimacy_allowed


def resolve_person(chat_or_person: str) -> str:
    return relationship_memory.resolve_person_id(chat_or_person)


def current_strategy(chat_or_person: str) -> dict:
    person_id = resolve_person(chat_or_person)
    return relationship_memory.load_strategy_profile(person_id) if person_id else {}


def generate_strategy_for_person(
    person_id: str,
    *,
    relationship_setting: str = "",
    notes: str = "",
    include_intimacy: bool | None = None,
) -> dict:
    person_id = relationship_memory.resolve_person_id(person_id)
    if not person_id:
        raise ValueError("人物不能为空")
    if not settings.has_llm_key():
        raise ValueError("请先在全局设置里配置起草模型密钥")

    person = relationship_memory.person_record(person_id)
    effective_relationship = relationship_setting or str(person.get("relationship") or "")
    allow_intimacy = intimacy_allowed(effective_relationship, explicit=include_intimacy)

    # 原始 source_items 是审计档案，不直接塞给策略模型。
    # 只有经过 memories / relationship_snapshots / intimacy_preferences 证据层整理后的内容才能驱动策略。
    generated = interaction_strategy.generate(
        person_profile=relationship_memory.profile_context(person_id, limit=160),
        relationship_context=relationship_memory.relationship_context(person_id, limit=20),
        intimacy_context=relationship_memory.intimacy_context(person_id, limit=160) if allow_intimacy else "",
        relationship_setting=effective_relationship,
        notes=str(notes or "").strip(),
        provider=settings.draft_provider(),
        model=settings.draft_model() or "",
        base_url=settings.draft_base_url() or None,
        api_key=settings.llm_key(),
        thinking=settings.thinking(),
        include_intimacy=allow_intimacy,
    )
    source_id = interaction_strategy.profile_source_id(generated)
    relationship_memory.save_strategy_profile(
        person_id,
        generated,
        source_type="interaction-strategy",
        source_id=source_id,
    )
    return relationship_memory.load_strategy_profile(person_id)


def generate_strategy_for_chat(chat: str) -> dict:
    chat = str(chat or "").strip()
    if not chat:
        raise ValueError("尚未识别到聊天对象")
    person_id = relationship_memory.resolve_person_id(chat)
    if not relationship_memory.person_record(person_id):
        profile = chat_profiles.get(chat)
        relationship_memory.ensure_person(
            person_id,
            display_name=chat,
            relationship=str(profile.get("relationship") or "未设置"),
        )
    profile = chat_profiles.get(chat)
    return generate_strategy_for_person(
        person_id,
        relationship_setting=str(profile.get("relationship") or ""),
        notes=str(profile.get("notes") or ""),
        include_intimacy=None,
    )


def realtime_context(chat_or_person: str, *, include_intimacy: bool = False) -> str:
    profile = current_strategy(chat_or_person)
    return interaction_strategy.context_text(profile, include_intimacy=include_intimacy)
