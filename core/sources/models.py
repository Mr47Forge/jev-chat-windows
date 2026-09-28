# -*- coding: utf-8 -*-
"""平台无关的人物资料输入结构。

微信、抖音、QQ、Telegram、线下观察、手工粘贴最终都归一成 SourceItem。
平台只是来源元数据，不参与人物画像主键。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SOURCE_KINDS = {
    "observation",       # 用户自己的观察
    "target_statement",  # 对方明确说过的原话/事实
    "chat_paste",        # 粘贴的聊天
    "platform_import",   # 平台导入器
    "note",              # 其它补充
    "agent_chat",        # 只和分析 Agent 讨论，不作为新证据
}

PLATFORMS = {
    "manual": "手工输入",
    "offline": "线下观察",
    "wechat": "微信",
    "douyin": "抖音",
    "qq": "QQ",
    "telegram": "Telegram",
    "xiaohongshu": "小红书",
    "weibo": "微博",
    "other": "其他",
}


@dataclass(slots=True)
class SourceItem:
    person_id: str
    content: str
    source_kind: str = "observation"
    platform: str = "manual"
    author_role: str = "observer"
    external_id: str = ""
    source_time: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "SourceItem":
        self.person_id = str(self.person_id or "").strip()
        self.content = str(self.content or "").strip()
        self.source_kind = str(self.source_kind or "observation").strip()
        self.platform = str(self.platform or "manual").strip()
        self.author_role = str(self.author_role or "observer").strip()
        if not self.person_id:
            raise ValueError("person_id 不能为空")
        if not self.content:
            raise ValueError("content 不能为空")
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError("source_kind 无效")
        return self
