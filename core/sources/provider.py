# -*- coding: utf-8 -*-
"""外部平台适配器协议。

实时微信 OCR 只是当前第一个实现。未来抖音、QQ、Telegram 等只要实现这个协议，
人物分析、长期记忆、策略和导出层都不需要改。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import SourceItem


@runtime_checkable
class PersonSourceProvider(Protocol):
    provider_id: str

    def health(self) -> dict:
        ...

    def people(self) -> list[dict]:
        ...

    def items_for_person(self, person_id: str, **kwargs) -> list[SourceItem]:
        ...


@runtime_checkable
class LiveConversationProvider(Protocol):
    provider_id: str

    def available(self) -> bool:
        ...

    def current_conversation(self) -> dict:
        ...

    def recent_messages(self, limit: int = 50) -> list[SourceItem]:
        ...
