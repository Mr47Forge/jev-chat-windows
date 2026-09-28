# -*- coding: utf-8 -*-
"""微信历史数据边界。

这里只负责“用户明确选择的联系人”的历史导入/查询。
默认不扫描、不导入任何联系人。
"""

from .tracememo_provider import TraceMemoProvider, WeChatHistoryError

__all__ = ["TraceMemoProvider", "WeChatHistoryError"]
