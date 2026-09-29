# -*- coding: utf-8 -*-
"""把 Jev 实时判断翻成“经典术语 + 为什么这样回”。

权威顺序：
当前可见行为 -> interaction_task / best_action -> 回复。
M3、IOI/IOD、PUA 术语只做教学解释，绝不反向决定 best_action。
"""
from __future__ import annotations

_M3_LABELS = {
    "insufficient": "信息不足",
    "A1": "A1 · 开场/建立接触",
    "A2": "A2 · 对方兴趣",
    "A3": "A3 · 双向吸引确认",
    "C1": "C1 · 对话/熟悉",
    "C2": "C2 · 连接/信任",
    "C3": "C3 · 亲密连接",
    "S1": "S1 · 双方已进入亲密/性互动",
    "S2": "S2 · 出现犹豫，暂停确认",
    "S3": "S3 · 已明确发生双方同意的性行为",
}

_TASK_LABELS = {
    "initiate_contact": "发起/恢复接触",
    "observe_interest": "观察兴趣与互惠",
    "express_interest_filter": "表达兴趣 + 双向筛选",
    "build_connection": "建立连接",
    "build_trust": "建立/修复信任",
    "increase_intimacy": "承接已出现的亲密",
    "confirm_next_step": "确认双方下一步",
}


def _choice(answers: dict, key: str) -> str:
    return str(((answers or {}).get(key) or {}).get("choice") or "")


def _confidence(answers: dict, key: str):
    value = ((answers or {}).get(key) or {}).get("confidence")
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def build(answers: dict, recommended_reply: str = "") -> dict:
    answers = answers or {}
    tone = _choice(answers, "partner_tone")
    stage = _choice(answers, "relationship_stage")
    trend = _choice(answers, "interaction_trend")
    reciprocity = _choice(answers, "reciprocity")
    task = _choice(answers, "interaction_task")
    action = _choice(answers, "best_action")
    need = _choice(answers, "she_needs")
    intent = _choice(answers, "true_intent")
    m3_phase = _choice(answers, "m3_phase")

    terms = []

    if sum((
        tone in {"warm", "playful"},
        trend == "warming",
        reciprocity in {"balanced", "partner_more"},
    )) >= 2:
        terms.append({
            "term": "IOI",
            "label": "IOI · 兴趣/互惠信号",
            "confidence": _confidence(answers, "partner_tone"),
            "meaning": "当前可见互动同时出现多个正向互惠信号。",
            "note": "教学术语；表示当前互惠偏正向，不等于已经确定喜欢或承诺。",
        })

    if sum((
        tone == "withdrawing",
        trend == "cooling",
        reciprocity == "user_more",
    )) >= 2:
        terms.append({
            "term": "IOD",
            "label": "IOD · 低兴趣/撤回信号",
            "confidence": _confidence(answers, "interaction_trend"),
            "meaning": "当前可见互动同时出现收缩、降温或投入失衡。",
            "note": "教学术语；提示降低推进强度，不解释成“她在测试你”。",
        })

    if tone == "testing" or (intent == "confirm_you_care" and bool(stage or task or m3_phase)):
        terms.append({
            "term": "Frame",
            "label": "Frame · 框架/自身立场",
            "confidence": _confidence(answers, "true_intent"),
            "meaning": "当前更需要保持事实、态度和边界稳定，而不是为了求确认不断加码。",
            "note": "这里指清楚表达，不是争夺控制权。",
        })

    if task == "express_interest_filter":
        terms.append({
            "term": "Qualification",
            "label": "Qualification · 双向筛选",
            "confidence": _confidence(answers, "interaction_task"),
            "meaning": "双方兴趣已有一定基础，当前重点是了解适配，而不是单方面证明价值。",
            "note": "只作平等适配判断，不让对方证明“配不配”。",
        })

    if task == "confirm_next_step" and action in {"make_plan", "clarify_relationship"}:
        terms.append({
            "term": "Time Bridge",
            "label": "Time Bridge · 时间桥/下一步确认",
            "confidence": _confidence(answers, "interaction_task"),
            "meaning": "当前已有足够上下文，可以把互动连接到一个双方都能明确选择的下一步。",
            "note": "必须是真实、具体、可拒绝的下一步。",
        })

    if trend == "volatile":
        terms.append({
            "term": "Push-Pull",
            "label": "Push-Pull · 接近-退开波动",
            "confidence": _confidence(answers, "interaction_trend"),
            "meaning": "这里描述的是已经观察到的冷热/接近退开波动，不代表 Jev 建议故意制造这种波动。",
            "note": "描述性标签，不是本轮动作指令。",
        })

    logic = []
    if task and task != "insufficient":
        logic.append("当前功能任务：" + _TASK_LABELS.get(task, task) + "。这是狗头军师非漏斗式阶段意识，不要求按顺序通关。")
    if m3_phase and m3_phase != "insufficient":
        logic.append(
            "经典 M3 教学投影：" + _M3_LABELS.get(m3_phase, m3_phase)
            + "；这是按当前证据直接定位，仅用于理解原体系，不参与回复动作选择。"
        )

    need_logic = {
        "care": "对方当前更需要被认真听见/确认在意，先接住，不用技巧覆盖这个需要。",
        "action": "对方当前更需要具体行动或安排，回复应优先把可确认的信息说清楚。",
        "explanation": "对方当前更需要事实解释，先处理事实。",
        "apology": "对方当前更需要针对已知问题的道歉，先修复具体问题。",
        "nothing": "当前可能已经自然收尾，不强行制造新任务。",
    }
    if need in need_logic:
        logic.append(need_logic[need])

    action_logic = {
        "check_history": "本轮主动作是先核对真实历史，避免把记忆空缺用猜测填上。",
        "apologize": "本轮主动作是对已确认的问题道歉。",
        "give_commitment": "本轮主动作是给出能兑现的具体承诺。",
        "explain": "本轮主动作是解释已知事实。",
        "acknowledge": "本轮主动作是接住当前表达，不额外推进。",
        "say_less": "本轮主动作是少说，避免过度解释或强行续聊。",
        "make_plan": "本轮主动作是确认一个具体、低压力、可拒绝的安排。",
        "flirt_lightly": "本轮主动作是承接已经存在的暧昧张力；这不自动等于 Push-Pull。",
        "clarify_relationship": "本轮主动作是直接澄清已经显著存在的关系意图，而不是绕术语。",
        "repair": "本轮主动作是修复真实的不满/误解，先于其它推进。",
        "give_space": "本轮主动作是停止追加压力，让对方的边界/意愿变清楚。",
    }
    if action in action_logic:
        logic.append(action_logic[action])

    if recommended_reply:
        logic.append("最终推荐句应服从上面的唯一主动作；术语只解释，不另起一套指令。")

    tension = "维持"
    investment = "维持"
    space = "维持"
    if action == "flirt_lightly":
        tension, space = "略升", "增加"
    elif action in {"give_space", "say_less", "acknowledge"}:
        tension, space = ("降低" if action == "give_space" else "维持"), "增加"
        if reciprocity == "user_more":
            investment = "降低"
    elif action in {"make_plan", "clarify_relationship"}:
        space = "增加"
    elif action in {"repair", "apologize"}:
        tension = "降低"

    return {
        "terms": terms,
        "logic": logic,
        "energy": {
            "interaction_tension": tension,
            "user_investment": investment,
            "reciprocity_space": space,
            "target_self_worth": "不作为调整目标",
            "note": "“能级”是课程化比喻，不是标准心理学量表；这里只拆成张力、投入和互惠空间。",
        },
        "stage": stage,
        "interaction_task": task,
        "m3_phase": m3_phase,
        "m3_label": _M3_LABELS.get(m3_phase, m3_phase),
    }


def render_text(data: dict) -> str:
    if not data:
        return ""
    lines = []

    if data.get("interaction_task") and data.get("interaction_task") != "insufficient":
        lines += [
            "【当前功能任务】",
            "- " + _TASK_LABELS.get(str(data["interaction_task"]), str(data["interaction_task"])),
        ]

    if data.get("m3_phase") and data.get("m3_phase") != "insufficient":
        lines += [
            "【经典 M3 教学投影】",
            "- " + str(data.get("m3_label") or data.get("m3_phase")),
            "  按当前证据直接定位；仅用于理解原体系，不驱动回复。",
        ]

    if data.get("terms"):
        lines.append("【术语判读】")
        for item in data["terms"]:
            conf = item.get("confidence")
            suffix = f" · 把握 {round(conf * 100)}%" if isinstance(conf, (int, float)) else ""
            lines.append(f"- {item.get('label')}{suffix}")
            lines.append("  " + str(item.get("meaning") or ""))
            if item.get("note"):
                lines.append("  注：" + str(item["note"]))

    if data.get("logic"):
        lines.append("【为什么这样回】")
        for i, item in enumerate(data["logic"], 1):
            lines.append(f"{i}. {item}")

    energy = data.get("energy") or {}
    if energy:
        lines += [
            "【所谓“能级”拆开看】",
            f"- 互动张力：{energy.get('interaction_tension')}",
            f"- 你的投入：{energy.get('user_investment')}",
            f"- 给对方参与空间：{energy.get('reciprocity_space')}",
            f"- 对方自尊：{energy.get('target_self_worth')}",
            "- " + str(energy.get("note") or ""),
        ]
    return "\n".join(lines).strip()
