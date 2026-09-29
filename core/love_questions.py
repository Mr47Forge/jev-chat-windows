# -*- coding: utf-8 -*-
"""恋爱场景的实时判断题。

这一层只负责“当前聊天片段”的轻量关系判断，不做长期心理诊断。
设计参考并重新实现自两个 MIT 项目：
- she-love-me: https://github.com/863401402/she-love-me
  关系阶段、趋势、投入不对称、证据不足留白。
- goutoujunshi: https://github.com/shengjidaguai-china/goutoujunshi
  事实/推测/未知分离、互惠、边界、下一步行动和可退出原则。

完整版权说明见仓库 NOTICE。
"""

LOVE_QUESTIONS: dict = {
    "partner_tone": {
        "type": "choice",
        "instructions": (
            "What is the other person's observable interaction tone in the latest exchange? "
            "Judge only from visible wording and recent behavior. Do not infer a hidden mental state. "
            "If evidence is weak or mixed, choose unclear."
        ),
        "criteria": {
            "warm": "Open, engaged, caring, or clearly receptive.",
            "playful": "Light teasing, joking, banter, or flirtatious play without clear hostility.",
            "neutral": "Ordinary factual or logistical exchange without a strong emotional signal.",
            "testing": "They are checking attention, sincerity, memory, priority, or whether you care.",
            "hurt": "They visibly express disappointment, sadness, feeling ignored, or being let down.",
            "angry": "They visibly blame, confront, criticize, or escalate.",
            "withdrawing": "They are shortening, disengaging, ending contact, or asking for space.",
            "unclear": "The current snippet does not support a reliable tone classification.",
        },
    },
    "relationship_stage": {
        "type": "choice",
        "instructions": (
            "Based only on evidence available in this chat snippet, what relationship stage is supported RIGHT NOW? "
            "Classify from current evidence directly; this is NOT an adjacency ladder and may jump across labels when a strong current message supports it. "
            "Do not promote ordinary friendliness into romance. A serious explicit relationship/commitment proposal is stronger evidence than generic flirting, "
            "while an obvious joke should still be treated as a joke. If the snippet is too short or lacks evidence, choose insufficient. "
            "This is a descriptive interaction stage, not a diagnosis."
        ),
        "criteria": {
            "insufficient": "Not enough evidence to place the relationship on a romantic progression.",
            "early_probing": "Early contact, basic familiarity, tentative interest, or exploratory conversation.",
            "warming": "Mutual engagement is increasing; more personal sharing, playful interest, or repeated contact appears.",
            "ambiguous_push_pull": "There is attraction or investment but also hesitation, mixed signals, testing, or uneven pacing.",
            "pre_commitment": (
                "There are strong relationship-like signals, explicit romantic intent, future-oriented commitment talk, "
                "or a serious proposal to define/advance the relationship. This label can be selected directly from a strong current signal."
            ),
            "stable_relationship": (
                "The chat clearly reflects an established mutually recognized relationship. "
                "Use current direct evidence even if an earlier snippet was classified much lower."
            ),
            "cooling": "The recent interaction shows sustained reduction in warmth, initiative, openness, or willingness to engage.",
        },
    },
    "interaction_trend": {
        "type": "choice",
        "instructions": (
            "What short-term interaction trend is visible across the recent messages? "
            "Use behavior such as initiative, message depth, responsiveness, repair, and withdrawal. "
            "Do not guess from one emoji or one short reply. Choose insufficient when the window is too small."
        ),
        "criteria": {
            "warming": "Recent interaction is becoming more engaged, open, playful, cooperative, or intimate.",
            "stable": "No meaningful directional change is visible.",
            "cooling": "Recent interaction is becoming shorter, less responsive, less open, or more distant.",
            "volatile": "The interaction swings sharply between closeness and tension or approach and withdrawal.",
            "insufficient": "Not enough recent evidence to determine a trend.",
        },
    },
    "reciprocity": {
        "type": "choice",
        "instructions": (
            "Within the visible recent exchange, how balanced is observable effort? "
            "Use initiation, follow-up questions, topic continuation, repair attempts, and substantive engagement. "
            "Do not treat message count alone as affection. Choose insufficient if the sample is too small."
        ),
        "criteria": {
            "balanced": "Both sides contribute meaningful initiative and engagement at a roughly comparable level.",
            "user_more": "The user is visibly carrying more of the initiation, repair, questioning, or continuation.",
            "partner_more": "The other person is visibly carrying more of the initiative, repair, questioning, or continuation.",
            "insufficient": "The visible sample is too small or too one-sided to assess reciprocity reliably.",
        },
    },
    "m3_phase": {
        "type": "choice",
        "instructions": (
            "Classify the strongest Mystery Method M3 phase directly supported by the CURRENT visible interaction. "
            "This is a legacy social-training label, not a scientific diagnosis and NOT a required step-by-step sequence. "
            "Do not force adjacency: current evidence may jump from A1 directly to A3, C2, C3, S1, or another supported phase. "
            "Do not keep the answer artificially low because an earlier turn was lower. Also do not jump from one emoji or one joke. "
            "Explicit romantic, commitment, intimate, or sexual statements can be strong evidence when the surrounding tone shows they are serious. "
            "For S2, hesitation is a stop/pause signal, never something to push through."
        ),
        "criteria": {
            "insufficient": "Not enough evidence to map the current interaction to M3.",
            "A1": "Opening/contact only; interaction has started but reliable reciprocal interest is not yet supported.",
            "A2": "The other person shows observable interest/investment toward the user: initiative, extension, questions, playful engagement, or repeated IOIs.",
            "A3": "Mutual attraction is openly reciprocated; the other person's interest is already supported and the user is clearly returning interest.",
            "C1": "Conversation/rapport beyond the opening: both sides are genuinely getting to know each other.",
            "C2": "Connection/trust: sustained personal sharing, repeated contact, meaningful familiarity, or stronger relational connection is directly supported.",
            "C3": "Strong personal/romantic intimacy or close relationship-like interaction is directly supported.",
            "S1": "Mutually initiated sexual/physical intimacy is directly present; generic flirting or sexual jokes alone are not enough.",
            "S2": "Hesitation, ambivalence, or withdrawal appears around an already sexual/physical situation; the correct implication is pause and clarify willingness.",
            "S3": "Consensual sexual activity is explicitly stated as already occurring or having occurred; never infer this from flirting or sexual talk alone."
        },
    },
    "love_action": {
        "type": "choice",
        "instructions": (
            "What relationship-level next move best fits this exact moment? "
            "Prefer the smallest useful action. Do not optimize for 'winning' the person. "
            "Respect reciprocity and explicit boundaries. If the other person clearly asks for space, rejects contact, "
            "or shows discomfort, choose give_space. If key facts are missing, choose check_history rather than inventing."
        ),
        "criteria": {
            "respond_lightly": "Keep the exchange easy and natural; no need to escalate or define the relationship.",
            "show_care": "Acknowledge feelings, attention, or importance without overpromising.",
            "flirt_lightly": "A small playful or flirtatious step is supported and still easy for either side to exit.",
            "clarify": "Reduce ambiguity by calmly asking or stating one important point.",
            "invite": "Suggest one concrete, low-pressure next interaction or meeting because reciprocity supports it.",
            "repair": "Address a real hurt, misunderstanding, or conflict before trying to advance.",
            "give_space": "Stop pushing and reduce contact because the other person asked for space, rejected, or is visibly withdrawing.",
            "check_history": "Verify prior facts, promises, or context before replying substantively.",
        },
    },
}

LOVE_CHOICE_LABELS: dict = {
    "partner_tone": {
        "warm": "温暖投入", "playful": "轻松调侃", "neutral": "普通交流",
        "testing": "在试探你", "hurt": "明显受伤", "angry": "明显生气",
        "withdrawing": "正在收缩互动", "unclear": "信息不足",
    },
    "relationship_stage": {
        "insufficient": "信息不足", "early_probing": "初识试探期", "warming": "暧昧升温期",
        "ambiguous_push_pull": "暧昧拉锯期", "pre_commitment": "关系确认前",
        "stable_relationship": "稳定关系期", "cooling": "降温期",
    },
    "interaction_trend": {
        "warming": "升温", "stable": "平稳", "cooling": "降温",
        "volatile": "冷热波动", "insufficient": "信息不足",
    },
    "reciprocity": {
        "balanced": "投入较平衡", "user_more": "你投入更多",
        "partner_more": "对方投入更多", "insufficient": "信息不足",
    },
    "m3_phase": {
        "insufficient": "M3 信息不足",
        "A1": "A1 · 开场/建立接触",
        "A2": "A2 · 对方兴趣",
        "A3": "A3 · 双向吸引确认",
        "C1": "C1 · 对话/熟悉",
        "C2": "C2 · 连接/信任",
        "C3": "C3 · 亲密连接",
        "S1": "S1 · 双方已进入亲密/性互动",
        "S2": "S2 · 出现犹豫，暂停确认",
        "S3": "S3 · 已明确发生双方同意的性行为",
    },
    "love_action": {
        "respond_lightly": "自然接话", "show_care": "表达在意", "flirt_lightly": "轻度调情",
        "clarify": "澄清一个关键点", "invite": "低压力邀约", "repair": "先修复关系",
        "give_space": "给对方空间", "check_history": "先核对聊天记录",
    },
}

LOVE_GUIDE_FIELDS = (
    ("partner_tone", "对方当前状态"),
    ("relationship_stage", "关系阶段"),
    ("interaction_trend", "互动趋势"),
    ("reciprocity", "近期互惠"),
    ("m3_phase", "M3 实时阶段"),
    ("love_action", "关系策略"),
)
