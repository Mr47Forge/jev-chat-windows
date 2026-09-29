# -*- coding: utf-8 -*-
"""把 Jev 的实时关系判断翻成“术语 + 为什么这样回”。

这里只解释可观察信号和当前回复的逻辑，不参与候选生成。
"""
from __future__ import annotations


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
    action = _choice(answers, "love_action")
    need = _choice(answers, "she_needs")
    intent = _choice(answers, "true_intent")

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
            "meaning": "当前可见互动里出现较多主动延展、玩笑、升温或对方投入。",
            "note": "这是社交训练术语，不等于已经确定喜欢。",
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
            "meaning": "当前可见互动里出现收缩、降温或投入明显不平衡。",
            "note": "用于提示降低推进强度，不把单次短回复直接定性。",
        })

    if tone == "testing" or intent == "confirm_you_care":
        terms.append({
            "term": "Frame",
            "label": "Frame · 框架/节奏",
            "confidence": _confidence(answers, "true_intent"),
            "meaning": "当前重点是保持自己的事实、态度和边界稳定，不急着过度证明。",
            "note": "这里指保持清楚表达，不是争夺控制权。",
        })

    if action == "flirt_lightly":
        terms.append({
            "term": "Push-Pull",
            "label": "Push-Pull · 推拉（轻度张力版）",
            "confidence": _confidence(answers, "love_action"),
            "meaning": "当前只使用“轻调情后留回应空间”的部分。",
            "note": "不把制造不安或奖惩式互动作为目标。",
        })

    if action == "invite":
        terms.append({
            "term": "Time Bridge",
            "label": "Time Bridge · 时间桥",
            "confidence": _confidence(answers, "love_action"),
            "meaning": "把当前互动自然连接到一个具体、低压力的下一步。",
            "note": "下一步仍由双方明确决定。",
        })

    if action == "clarify":
        terms.append({
            "term": "Cold Read",
            "label": "Cold Read · 冷读（开放假设版）",
            "confidence": _confidence(answers, "love_action"),
            "meaning": "当前信息有歧义，优先提出可纠正的假设或直接澄清。",
            "note": "不把猜测包装成已经看穿对方。",
        })

    logic = []
    if need == "care":
        logic.append("当前首先解决“被认真听见/被在意”的需要，所以避免长篇解释或连续追问。")
    elif need == "action":
        logic.append("当前主要需要具体行动或安排，所以回复应把信息说清楚，而不是用情绪话术代替行动。")
    elif need == "explanation":
        logic.append("当前主要需要事实解释，所以先解决事实问题。")
    elif need == "apology":
        logic.append("当前主要是修复已经确认的问题，所以先承认具体问题。")
    elif need == "nothing":
        logic.append("当前可能已经自然收尾，所以不强行续话题。")

    if action == "flirt_lightly":
        logic.append("关系信号允许轻微增加张力，但仍把回应权留给对方。")
    elif action == "respond_lightly":
        logic.append("当前不需要升级，正常接住比强行推进更匹配关系阶段。")
    elif action == "give_space":
        logic.append("当前信号偏收缩，减少追加内容可以让互惠重新变清楚。")
    elif action == "invite":
        logic.append("当前互惠足够，把线上互动转成一次具体、可拒绝的下一步更有信息量。")
    elif action == "repair":
        logic.append("先处理真实的不满或误解，再考虑其它关系动作。")
    elif action == "clarify":
        logic.append("当前关键问题是信息不确定，先澄清比继续猜更稳。")

    if recommended_reply:
        logic.append("最终推荐句是候选中最符合上述动作、关系阶段和当前节奏的一条。")

    tension = "维持"
    investment = "维持"
    space = "维持"
    if action == "flirt_lightly":
        tension, space = "略升", "增加"
    elif action in {"give_space", "respond_lightly"}:
        tension, space = "降低", "增加"
        if reciprocity == "user_more":
            investment = "降低"
    elif action == "invite":
        tension, space = "略升", "增加"
    elif action in {"repair", "show_care"}:
        tension = "降低"

    return {
        "terms": terms,
        "logic": logic,
        "energy": {
            "interaction_tension": tension,
            "user_investment": investment,
            "reciprocity_space": space,
            "target_self_worth": "不作为调整目标",
            "note": "“能级”不是标准心理学量表，这里拆成互动张力、你的投入和互惠空间。",
        },
        "stage": stage,
    }


def render_text(data: dict) -> str:
    if not data:
        return ""
    lines = []
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
