# -*- coding: utf-8 -*-
"""实时关系策略路由。

“best_action”是唯一动作权威。阶段、M3、IOI/IOD、长期画像只能解释背景，
不能各自再产生一套冲突动作。
"""
from __future__ import annotations

try:
    from .goutou_guidance import context_for as goutou_context
except ImportError:
    from goutou_guidance import context_for as goutou_context


def choice(answers: dict, key: str) -> str:
    return str(((answers or {}).get(key) or {}).get("choice") or "")


def probability(answers: dict, key: str) -> float | None:
    value = ((answers or {}).get(key) or {}).get("noul")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def needs_history(answers: dict) -> bool:
    return choice(answers, "best_action") == "check_history"


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
        "- 只依据聊天中已经出现的事实；未知保持未知。",
        "- 本轮只有一个主要动作，不让多个模块各自下命令。",
        "- M3、IOI/IOD、人格画像都是解释层，不能覆盖 best_action。",
        "- 尊重明确边界，不把普通友好自动解释成亲密关系升级。",
    ]

    action = choice(answers, "best_action")
    task = choice(answers, "interaction_task")
    need = choice(answers, "she_needs")

    action_lines = {
        "check_history": "先核对已有聊天中的约定或事实；核对前不要猜测或假装记得。",
        "apologize": "针对已经确认的具体问题道歉，不为未知事实乱认错。",
        "give_commitment": "只给当前确实能兑现的具体承诺或安排。",
        "explain": "解释已知事实和原因，不补造缺失信息。",
        "acknowledge": "先接住对方当前表达，不为了推进而额外加任务。",
        "say_less": "当前多说会变差，保持短回应或自然收尾。",
        "make_plan": "把当前互惠转成一个具体、低压力、可拒绝的安排。",
        "flirt_lightly": "只承接已经存在的暧昧张力，不把普通友好硬推成暧昧。",
        "clarify_relationship": "当前关系意图已经值得澄清，直接、低压力地确认。",
        "repair": "先修复真实的不满/误解，再谈任何推进。",
        "give_space": "对方正在收缩或要求空间，停止追加推进。",
    }
    if action in action_lines:
        lines.append("- 本轮主要动作：" + action_lines[action])

    need_lines = {
        "apology": "针对已确认问题的道歉。",
        "action": "具体行动或安排。",
        "explanation": "事实解释。",
        "care": "被认真听见和重视。",
        "nothing": "当前不需要新内容，避免强行续聊。",
    }
    if need in need_lines:
        lines.append("- 对方当前需要：" + need_lines[need])

    if history_checked:
        lines.append("- 本轮已经读取真实历史；只能使用历史里确实出现的信息。")
    if should_stop(answers):
        lines.append("- 当前满足停止条件：自然收尾，不再制造新任务或话题。")

    upstream = goutou_context(task, action)
    if upstream:
        lines.append(upstream)
    return "\n".join(lines)
