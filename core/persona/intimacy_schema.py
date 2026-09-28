# -*- coding: utf-8 -*-
"""亲密/性偏好画像的统一维度表。

这是人物画像 schema，不是诊断工具，也不代表现实同意。
任何从聊天推测出的内容都必须保存为 inferred，并附证据与置信度。
"""

SCOPES = {
    "topic_interest": "话题兴趣",
    "fantasy": "幻想偏好",
    "real_world_willingness": "现实尝试意愿",
    "experience": "实际经历",
    "boundary": "明确边界",
}

DIMENSIONS = {
    "power_exchange": "权力交换/主导-顺从",
    "dominance": "主导/强势倾向",
    "submission": "顺从/被主导倾向",
    "switching": "主导与顺从切换",
    "pain_receiving": "疼痛刺激接受偏好",
    "pain_giving": "施加疼痛刺激偏好",
    "exhibitionism": "展示/被观看刺激",
    "voyeurism": "观看刺激",
    "risk_novelty": "新鲜感/风险刺激",
    "restraint": "束缚/限制感",
    "humiliation": "羞耻/贬低类互动",
    "praise": "赞美/认可类互动",
    "roleplay": "角色扮演",
    "control": "掌控/被掌控感",
    "initiation": "主动/被主动偏好",
    "touch": "身体接触偏好",
    "naming": "称呼/角色称谓偏好",
    "sexual_communication": "亲密话题表达方式",
    "aftercare": "事后安抚/照顾偏好",
    "other": "其他反复出现的特殊偏好",
}

ANALYSIS_RULES = (
    "一次玩笑、一次转发、一次好奇不能建立长期敏感画像。",
    "普通性格强势不能直接推出性方面偏好主导；自卑也不能直接推出顺从或受虐偏好。",
    "话题兴趣、幻想、现实意愿、实际经历、明确边界必须分开。",
    "推测必须有跨时间或重复证据，并保留反证；证据不足就是未知。",
    "现实意愿、实际经历和边界不能由幻想自动升级。",
    "任何现实行为都只以当下明确、自愿、可撤回的同意为准。",
)
