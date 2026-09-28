# -*- coding: utf-8 -*-
"""Conversation strategy routing helpers.

The module keeps orchestration separate from UI and model clients.
Reference framework attribution is documented in NOTICE.
"""
from __future__ import annotations


def choice(answers: dict, key: str) -> str:
    return str(((answers or {}).get(key) or {}).get("choice") or "")


def probability(answers: dict, key: str) -> float | None:
    value = ((answers or {}).get(key) or {}).get("noul")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def needs_history(answers: dict) -> bool:
    return (
        choice(answers, "best_action") == "check_history"
        or choice(answers, "love_action") == "check_history"
    )


def should_stop(answers: dict) -> bool:
    resolved = probability(answers, "tension_resolved")
    return bool(
        resolved is not None
        and resolved >= 0.5
        and (
            choice(answers, "she_needs") == "nothing"
            or choice(answers, "true_intent") == "close_topic"
        )
    )


def strategy_context(relationship: str, answers: dict, history_checked: bool = False) -> str:
    lines = [
        "关系沟通策略参考：",
        "- 只依据聊天中已经出现的事实；未知信息保持未知。",
        "- 一次只处理当前最重要的问题，优先最小有效动作。",
        "- 尊重明确边界，不把普通友好自动解释成亲密关系升级。",
    ]
    action = choice(answers, "best_action")
    love_action = choice(answers, "love_action")
    need = choice(answers, "she_needs")

    if action == "check_history" or love_action == "check_history":
        lines.append("- 先核对已有聊天中的约定或事实；核对前不要猜测或假装记得。")
    if need == "apology":
        lines.append("- 当前重点是针对已经确认的具体问题道歉。")
    elif need == "action":
        lines.append("- 当前重点是具体行动或安排，不要用长篇解释替代行动。")
    elif need == "explanation":
        lines.append("- 当前重点是解释已知事实和原因，不补造缺失信息。")
    elif need == "care":
        lines.append("- 当前重点是让对方感到被认真听见和重视，避免空泛保证。")
    elif need == "nothing":
        lines.append("- 当前可能已经收尾，避免继续翻旧账或强行推进。")

    if history_checked:
        lines.append("- 本轮已经扩大读取历史；只使用历史中真实出现的信息。")
    if should_stop(answers):
        lines.append("- 当前满足停止条件：回复应以自然收尾为主，不再制造新的任务或话题。")
    return "\n".join(lines)


if __name__ == "__main__":
    assert needs_history({"best_action": {"choice": "check_history"}})
    assert should_stop({"tension_resolved": {"noul": 0.9}, "she_needs": {"choice": "nothing"}})
    print("relationship_strategy ok")
