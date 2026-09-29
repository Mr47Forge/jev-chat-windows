# -*- coding: utf-8 -*-
"""亲密画像批量分析服务。

只接收已经由上层确认的单个 person_id 和其真实历史消息；来源可以是微信、QQ、抖音或其它平台。
调用本服务本身就代表用户明确要求做亲密/性偏好批量分析。
"""
from __future__ import annotations

from app import settings
from core.persona.intimacy_profiler import analyze_history


def analyze_selected_history(
    person_id: str,
    messages: list[dict],
    *,
    batch_size: int = 180,
) -> list[dict]:
    if not settings.has_llm_key():
        raise ValueError("请先在全局设置中配置起草模型密钥")
    provider = settings.draft_provider()
    return analyze_history(
        person_id,
        messages,
        provider=provider,
        model=settings.draft_model() or "",
        base_url=settings.draft_base_url() or None,
        api_key=settings.llm_key(),
        thinking=settings.thinking(),
        batch_size=batch_size,
    )
