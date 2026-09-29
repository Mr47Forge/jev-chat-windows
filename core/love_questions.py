# -*- coding: utf-8 -*-
"""恋爱场景实时关系判断题。

职责拆分：
- relationship_stage：关系状态；
- interaction_trend：短期方向；
- interaction_task：当前功能任务；
- m3_phase：经典 M3 教学投影，只解释，不驱动回复；
- best_action（core/questions.py）：本轮唯一主要动作。
"""

LOVE_QUESTIONS: dict = {
    "partner_tone": {
        "type": "choice",
        "instructions": (
            "What is the other person's OBSERVABLE interaction tone in the latest exchange? "
            "Judge visible wording and recent behavior only. Do not infer a hidden personality or diagnosis. "
            "If evidence is weak or mixed, choose unclear."
        ),
        "criteria": {
            "warm": "Open, engaged, caring, or clearly receptive.",
            "playful": "Light teasing, joking, banter, or flirtatious play without clear hostility.",
            "neutral": "Ordinary factual or logistical exchange without a strong emotional signal.",
            "testing": "They are visibly checking attention, sincerity, memory, priority, or whether you care.",
            "hurt": "They visibly express disappointment, sadness, feeling ignored, or being let down.",
            "angry": "They visibly blame, confront, criticize, or escalate.",
            "withdrawing": "They are shortening, disengaging, ending contact, or asking for space.",
            "unclear": "The current snippet does not support a reliable tone classification.",
        },
    },
    "relationship_stage": {
        "type": "choice",
        "instructions": (
            "Classify the relationship STATUS directly supported RIGHT NOW by the visible chat and explicitly supplied relationship label. "
            "This field is NOT a trend field: do not use warming/cooling/push-pull here. "
            "It is NOT an adjacency ladder and may jump when strong current evidence supports it. "
            "A serious explicit relationship/commitment proposal is stronger evidence than generic flirting; an obvious joke is not. "
            "Choose insufficient when current evidence and explicit label do not support a reliable status."
        ),
        "criteria": {
            "insufficient": "The current evidence is not enough to place the relationship reliably.",
            "early_contact": "New or lightly familiar contact; no reliable mutual romantic interest is established.",
            "familiar_or_friend": "Clear familiarity or friendship-like connection, but current evidence does not establish mutual romance.",
            "mutual_romantic_interest": "Both sides visibly reciprocate romantic attraction or affection, but the relationship is not yet functioning like dating/partnership.",
            "dating_or_undefined": "They are dating, behaving relationship-like, or mutually intimate while formal status remains undefined/ambiguous.",
            "pre_commitment": "There is explicit serious intent to define, commit to, or materially advance the relationship.",
            "stable_relationship": "The chat/explicit label clearly reflects an established mutually recognized romantic relationship.",
            "former_relationship": "The relationship has clearly ended or the people are discussing an already-ended romantic relationship.",
        },
    },
    "interaction_trend": {
        "type": "choice",
        "instructions": (
            "What SHORT-TERM directional trend is visible across the recent messages? "
            "Use initiative, message depth, responsiveness, repair, openness, and withdrawal. "
            "Do not turn a single emoji or one short reply into a trend."
        ),
        "criteria": {
            "warming": "Recent interaction is becoming more engaged, open, playful, cooperative, or intimate.",
            "stable": "No meaningful directional change is visible.",
            "cooling": "Recent interaction is becoming shorter, less responsive, less open, or more distant.",
            "volatile": "Recent interaction swings sharply between approach/withdrawal or warmth/tension.",
            "insufficient": "Not enough recent evidence to determine a direction.",
        },
    },
    "reciprocity": {
        "type": "choice",
        "instructions": (
            "Within the visible recent exchange, how balanced is OBSERVABLE effort? "
            "Use initiation, follow-up questions, topic continuation, repair attempts, and substantive engagement. "
            "Do not treat raw message count alone as affection."
        ),
        "criteria": {
            "balanced": "Both sides contribute meaningful initiative and engagement at a roughly comparable level.",
            "user_more": "The user is visibly carrying more initiation, repair, questioning, or continuation.",
            "partner_more": "The other person is visibly carrying more initiative, repair, questioning, or continuation.",
            "insufficient": "The visible sample is too small or one-sided to assess reciprocity reliably.",
        },
    },
    "interaction_task": {
        "type": "choice",
        "instructions": (
            "Using the non-funnel Mystery/goutoujunshi translation, which FUNCTIONAL relationship task best describes the current interaction? "
            "This is a descriptive task label, not a right to escalate and not a required sequence. "
            "Choose directly from current evidence; tasks may be skipped or revisited."
        ),
        "criteria": {
            "insufficient": "No reliable relationship task can be identified from the current exchange.",
            "initiate_contact": "The main function is simply starting/restarting contact in a low-pressure way.",
            "observe_interest": "The main function is observing whether interest/engagement is actually reciprocal.",
            "express_interest_filter": "Mutual interest is sufficiently present that the interaction is expressing interest while learning fit/compatibility.",
            "build_connection": "The exchange is primarily deepening familiarity through reciprocal conversation and self-disclosure.",
            "build_trust": "The exchange is primarily about reliability, repair, consistency, vulnerability, or emotional safety.",
            "increase_intimacy": "Both sides are already engaging in a more intimate/romantic topic and the current task is responding to that existing intimacy.",
            "confirm_next_step": "The current interaction is ready for a mutually clear next step such as a plan or relationship clarification.",
        },
    },
    "m3_phase": {
        "type": "choice",
        "instructions": (
            "Educational projection only: classify the strongest classic Mystery Method M3 label supported by the CURRENT visible interaction. "
            "This label MUST NOT control the reply action. It is not scientific and not a required sequence. Do not force adjacency; it is not an adjacency ladder. "
            "Do not keep it low because an earlier turn was lower; do not jump from one joke or emoji. "
            "For S2, hesitation means pause/clarify willingness, never something to overcome."
        ),
        "criteria": {
            "insufficient": "Not enough evidence to map the current interaction to a classic M3 label.",
            "A1": "Opening/contact only; reliable reciprocal interest is not yet supported.",
            "A2": "The other person shows observable interest/investment: initiative, extension, questions, playful engagement, or repeated IOIs.",
            "A3": "Mutual attraction is openly reciprocated; both sides are clearly returning romantic interest.",
            "C1": "Conversation/rapport beyond opening: both sides are genuinely getting to know each other.",
            "C2": "Connection/trust: sustained personal sharing, repeated contact, meaningful familiarity, or stronger connection is supported.",
            "C3": "Strong personal/romantic intimacy or close relationship-like interaction is supported.",
            "S1": "Mutually initiated sexual/physical intimacy is directly present; generic flirting or sexual jokes are not enough.",
            "S2": "Hesitation/ambivalence/withdrawal appears around an already sexual/physical situation; pause and clarify willingness.",
            "S3": "Consensual sexual activity is explicitly stated as already occurring or having occurred; never infer it from sexual talk alone.",
        },
    },
}

LOVE_CHOICE_LABELS: dict = {
    "partner_tone": {
        "warm": "温暖投入", "playful": "轻松调侃", "neutral": "普通交流",
        "testing": "在确认你的态度/注意", "hurt": "明显受伤", "angry": "明显生气",
        "withdrawing": "正在收缩互动", "unclear": "信息不足",
    },
    "relationship_stage": {
        "insufficient": "信息不足",
        "early_contact": "初识/轻熟悉",
        "familiar_or_friend": "熟悉/朋友连接",
        "mutual_romantic_interest": "双向浪漫兴趣",
        "dating_or_undefined": "约会中/关系未定义",
        "pre_commitment": "关系确认/承诺前",
        "stable_relationship": "稳定关系",
        "former_relationship": "已结束的关系",
    },
    "interaction_trend": {
        "warming": "升温", "stable": "平稳", "cooling": "降温",
        "volatile": "冷热波动", "insufficient": "信息不足",
    },
    "reciprocity": {
        "balanced": "投入较平衡", "user_more": "你投入更多",
        "partner_more": "对方投入更多", "insufficient": "信息不足",
    },
    "interaction_task": {
        "insufficient": "任务信息不足",
        "initiate_contact": "发起/恢复接触",
        "observe_interest": "观察兴趣与互惠",
        "express_interest_filter": "表达兴趣 + 双向筛选",
        "build_connection": "建立连接",
        "build_trust": "建立/修复信任",
        "increase_intimacy": "承接已出现的亲密",
        "confirm_next_step": "确认双方下一步",
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
}

# m3_phase 故意不传给起草：只用于 UI 教学解释，不能反向控制回复。
LOVE_GUIDE_FIELDS = (
    ("partner_tone", "对方当前状态"),
    ("relationship_stage", "关系状态"),
    ("interaction_trend", "互动趋势"),
    ("reciprocity", "近期互惠"),
    ("interaction_task", "当前关系任务"),
)
