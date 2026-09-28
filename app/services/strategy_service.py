# -*- coding: utf-8 -*-
"""人物互动攻略服务：平台无关。"""
from __future__ import annotations

from app import chat_profiles, relationship_memory, settings
from core.persona import interaction_strategy


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
) -> dict:
    person_id = relationship_memory.resolve_person_id(person_id)
    if not person_id:
        raise ValueError("人物不能为空")
    if not settings.has_llm_key():
        raise ValueError("请先在全局设置里配置起草模型密钥")

    person = relationship_memory.person_record(person_id)
    sources = relationship_memory.source_items(person_id, limit=80)
    raw_source_text = "\n".join(
        f"[{x.get('platform')} / {x.get('source_kind')}] {str(x.get('content') or '').strip()}"
        for x in sources[-40:]
        if str(x.get("content") or "").strip()
    )[-12000:]
    merged_notes = str(notes or "").strip()
    if raw_source_text:
        merged_notes = (merged_notes + "\n\n原始资料摘录：\n" + raw_source_text).strip()

    generated = interaction_strategy.generate(
        person_profile=relationship_memory.profile_context(person_id, limit=160),
        relationship_context=relationship_memory.relationship_context(person_id, limit=20),
        intimacy_context=relationship_memory.intimacy_context(person_id, limit=160),
        relationship_setting=relationship_setting or str(person.get("relationship") or ""),
        notes=merged_notes,
        provider=settings.draft_provider(),
        model=settings.draft_model() or "",
        base_url=settings.draft_base_url() or None,
        api_key=settings.llm_key(),
        thinking=settings.thinking(),
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
            relationship=str(profile.get("relationship") or "恋爱对象"),
        )
    profile = chat_profiles.get(chat)
    return generate_strategy_for_person(
        person_id,
        relationship_setting=str(profile.get("relationship") or ""),
        notes=str(profile.get("notes") or ""),
    )


def realtime_context(chat_or_person: str, *, include_intimacy: bool = False) -> str:
    profile = current_strategy(chat_or_person)
    return interaction_strategy.context_text(profile, include_intimacy=include_intimacy)
