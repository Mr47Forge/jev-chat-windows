# -*- coding: utf-8 -*-
"""从 vendored 狗头军师资料中提取少量、与当前任务直接相关的策略依据。

设计目标：
- 真正让上游知识参与起草，而不是“复制进 vendor 就算接入”；
- 只提取少量相关片段，避免每轮把整个知识库塞进 prompt；
- 它只能补充 best_action 的执行方式，不能自己重新决定动作。
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BASE = _ROOT / "vendor" / "goutoujunshi"

_PATHS = {
    "observe_interest": [
        "references/practical/关系投入失衡：互惠判断、降级投入与退出决策.md",
        "references/practical/场景感、松弛感与社交校准：从接话到关系推进.md",
    ],
    "express_interest_filter": [
        "references/practical/自然流、内在状态与结构化互动：伦理能力转译.md",
        "references/practical/聊天化被动为主动：引导互动的实用指南.md",
    ],
    "build_connection": [
        "references/practical/巧妙接话技巧：让沟通更流畅的实用指南.md",
        "references/practical/为他人提供情绪价值：温暖且有效的回应指南.md",
    ],
    "build_trust": [
        "references/practical/万能吵架技巧：理性冲突处理指南.md",
        "references/practical/长期记忆与关系档案.md",
    ],
    "increase_intimacy": [
        "references/knowledge/08-同意边界性与亲密.md",
        "references/practical/主动表达、第一次见面与自然接触.md",
    ],
    "confirm_next_step": [
        "references/practical/主动表达、第一次见面与自然接触.md",
        "references/practical/实战话术编排器：从一句回复到后续分支.md",
    ],
    "repair": [
        "references/practical/万能吵架技巧：理性冲突处理指南.md",
        "references/practical/为他人提供情绪价值：温暖且有效的回应指南.md",
    ],
    "give_space": [
        "references/practical/关系投入失衡：互惠判断、降级投入与退出决策.md",
        "references/practical/高情商拒绝他人：体面护边界的实用指南.md",
    ],
    "flirt_lightly": [
        "references/practical/场景感、松弛感与社交校准：从接话到关系推进.md",
        "references/practical/自然流、内在状态与结构化互动：伦理能力转译.md",
    ],
    "clarify_relationship": [
        "references/practical/实战话术编排器：从一句回复到后续分支.md",
        "references/practical/主动表达、第一次见面与自然接触.md",
    ],
    "apologize": [
        "references/practical/万能吵架技巧：理性冲突处理指南.md",
    ],
    "acknowledge": [
        "references/practical/为他人提供情绪价值：温暖且有效的回应指南.md",
    ],
}

_KEYWORDS = {
    "observe_interest": ("互惠", "投入", "兴趣", "边界", "追问"),
    "express_interest_filter": ("筛选", "兴趣", "表达", "校准", "自然"),
    "build_connection": ("连接", "倾听", "接话", "开放", "共情"),
    "build_trust": ("信任", "修复", "可靠", "一致", "冲突"),
    "increase_intimacy": ("同意", "边界", "亲密", "身体", "确认"),
    "confirm_next_step": ("下一步", "邀请", "见面", "安排", "拒绝"),
    "repair": ("修复", "道歉", "冲突", "理解", "责任"),
    "give_space": ("空间", "边界", "停止", "投入", "退出"),
    "flirt_lightly": ("调侃", "张力", "轻松", "校准", "回应"),
    "clarify_relationship": ("关系", "澄清", "意图", "确认", "表达"),
    "apologize": ("道歉", "责任", "修复", "具体"),
    "acknowledge": ("情绪", "接住", "理解", "倾听", "感受"),
}


@lru_cache(maxsize=64)
def _read(rel: str) -> str:
    path = (_BASE / rel).resolve()
    if not str(path).startswith(str(_BASE.resolve())) or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _blocks(text: str) -> list[str]:
    """按 Markdown 段落切块，去掉标题/表格噪声，保留短规则段。"""
    parts = re.split(r"\n\s*\n+", text or "")
    out = []
    for part in parts:
        p = re.sub(r"^#{1,6}\s*", "", part.strip(), flags=re.M)
        if not p or p.startswith("|"):
            continue
        if len(p) < 35 or len(p) > 900:
            continue
        out.append(p)
    return out


def context_for(interaction_task: str, best_action: str, *, max_chars: int = 1800) -> str:
    keys = []
    for key in (str(best_action or ""), str(interaction_task or "")):
        if key and key not in keys:
            keys.append(key)

    selected: list[tuple[int, str, str]] = []
    seen = set()
    for key in keys:
        words = _KEYWORDS.get(key, ())
        for rel in _PATHS.get(key, ()):
            for block in _blocks(_read(rel)):
                score = sum(1 for word in words if word in block)
                if score <= 0:
                    continue
                normalized = re.sub(r"\s+", " ", block)
                sig = normalized[:160]
                if sig in seen:
                    continue
                seen.add(sig)
                selected.append((score, rel, normalized))

    selected.sort(key=lambda x: (-x[0], len(x[2])))
    lines = []
    used = 0
    for _, rel, block in selected[:6]:
        item = f"- [{Path(rel).name}] {block}"
        if used + len(item) > max_chars:
            break
        lines.append(item)
        used += len(item)
    if not lines:
        return ""
    return "【狗头军师上游依据（只补充执行方式，不改变本轮主动作）】\n" + "\n".join(lines)
