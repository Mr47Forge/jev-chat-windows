# -*- coding: utf-8 -*-
"""Jev 各上游模块的权威边界。

不是把所有项目同时塞进实时 Prompt，而是规定“谁负责什么”，防止模块互相覆盖。
"""
from __future__ import annotations

MODULES = {
    "goutoujunshi": {
        "role": "relationship_strategy_framework",
        "authority": "strategy",
        "runtime": "active_guidance",
        "notes": "结构/素材/互惠/边界/表达；只补充 best_action 的执行方式。",
    },
    "wechat-persona": {
        "role": "big_five_30_facets",
        "authority": "batch_personality",
        "runtime": "schema_and_feature_reference",
        "notes": "Big Five/30 facets 与语言特征用于批量人格层，不参与单条实时状态判断。",
    },
    "o-mem": {
        "role": "memory_hierarchy",
        "authority": "memory",
        "runtime": "methodology",
        "notes": "工作记忆/事件/Persona 分层、相关性检索、增量更新。",
    },
    "personamem-v3": {
        "role": "evidence_lifecycle",
        "authority": "persona_evidence",
        "runtime": "methodology",
        "notes": "多证据交叉、矛盾、时间变化、短长期、停止条件；禁止相邻主题过度合并。",
    },
    "blaniel": {
        "role": "personality_schema_reference",
        "authority": "schema_only",
        "runtime": "reference_only",
        "allow_real_person_behavior_predictor": False,
        "notes": "可借 Big Five facets/依恋字段结构；其 AI 角色行为模拟器不用于真人诊断。",
    },
    "bigfive-llm-predictor": {
        "role": "evaluation_simulation_reference",
        "authority": "evaluation_only",
        "runtime": "reference_only",
        "allow_real_person_scoring": False,
        "notes": "原项目用于模型扮演来访者回答 BFI，不当作真人聊天人格测评器。",
    },
    "kinkdirectory": {
        "role": "intimacy_taxonomy",
        "authority": "taxonomy",
        "runtime": "taxonomy_only",
    },
    "klist": {
        "role": "intimacy_long_tail_taxonomy",
        "authority": "taxonomy",
        "runtime": "taxonomy_only",
    },
    "relationship-atlas": {
        "role": "relationship_role_taxonomy",
        "authority": "taxonomy",
        "runtime": "taxonomy_only",
    },
    "kinkxknow": {
        "role": "questionnaire_role_scoring",
        "authority": "questionnaire_only",
        "runtime": "questionnaire_only",
        "allow_chat_inferred_scoring": False,
        "notes": "权重只接受显式问卷/用户确认输入，不把 LLM 从聊天猜出的特征冒充问卷答案。",
    },
}

_ROMANTIC = {
    "恋爱对象", "暧昧对象", "恋人", "暧昧", "伴侣", "对象", "情侣", "女朋友", "男朋友", "配偶",
    "partner", "romantic", "romantic partners", "dating", "lover", "girlfriend", "boyfriend",
}
_NON_ROMANTIC = {
    "未设置", "朋友", "同事", "家人", "其他", "friends", "friend",
    "coworker", "colleague", "colleagues", "family", "other", "unknown",
}


def normalize_relationship(value: str) -> str:
    raw = str(value or "").strip()
    low = raw.casefold()
    if raw in _ROMANTIC or low in _ROMANTIC:
        return "romantic"
    if raw in _NON_ROMANTIC or low in _NON_ROMANTIC:
        return "nonromantic"
    return "unknown"


def is_romantic_relationship(value: str) -> bool:
    return normalize_relationship(value) == "romantic"


def intimacy_allowed(value: str, explicit: bool | None = None) -> bool:
    """显式开关优先；没有开关时只在明确恋爱/暧昧/伴侣关系下启用。"""
    if explicit is not None:
        return bool(explicit)
    return is_romantic_relationship(value)


def realtime_relationship_enabled(value: str) -> bool:
    """朋友、同事、家人默认不跑恋爱/M3实时题。"""
    return is_romantic_relationship(value)


def module(name: str) -> dict:
    return dict(MODULES.get(str(name), {}))
