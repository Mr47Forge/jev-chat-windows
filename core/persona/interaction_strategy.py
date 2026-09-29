# -*- coding: utf-8 -*-
"""把“她是什么样的人”转换成“你具体怎么相处、怎么推进”的互动攻略。

输入来自长期人物记忆、关系趋势和亲密偏好；输出是可追溯的策略画像。
策略不是事实，不能覆盖 explicit 人物事实，也不能把性幻想当现实意愿。
"""
from __future__ import annotations

import json
from hashlib import sha1

from core import llm, providers

SCHEMA = "jev-interaction-strategy/v1"

INTIMACY_TOPIC_DEPTH = [
    {"level": 0, "name": "普通聊天", "description": "日常话题、兴趣、生活近况"},
    {"level": 1, "name": "吸引与欣赏", "description": "外貌、气质、能力、具体欣赏"},
    {"level": 2, "name": "轻暧昧", "description": "双方能自然接住的调侃、好感表达"},
    {"level": 3, "name": "亲密距离", "description": "拥抱、接吻、身体距离等泛亲密话题"},
    {"level": 4, "name": "亲密关系观", "description": "亲密边界、主动/被动、关系期待"},
    {"level": 5, "name": "性与欲望泛话题", "description": "不要求披露细节的性观念、欲望和沟通"},
    {"level": 6, "name": "个人亲密偏好", "description": "双方愿意时谈自己的偏好、喜欢与不喜欢"},
    {"level": 7, "name": "具体性偏好", "description": "具体角色、性癖、幻想、实践意愿与边界"},
    {"level": 8, "name": "现实协商", "description": "双方明确讨论现实行为、保护、边界和持续同意"},
]
# 兼容旧调用；语义已经明确为“话题深度”，不是关系阶段。
INTIMACY_LADDER = INTIMACY_TOPIC_DEPTH

SYSTEM = """你是 Jev 的长期互动策略分析器。输入是一个成年目标对象的长期人物画像、关系趋势、
亲密/性偏好证据，以及当前会话关系设置。任务不是重新描述她，而是把已有证据转换成
“和这个人具体怎么相处、怎么夸、怎么聊天、怎么安抚、关系如何小步推进”的可执行说明。

硬规则：
1. 只使用输入中已有证据。未知就是未知，不补人格、不补性偏好。
2. 明确事实优先于推测；策略结论本身只能是策略，不能回写成对方事实。
3. 每条建议尽量说明“为什么适合她”，并引用输入中的事实/推测文字作为 evidence。
4. 不给“保证成功”“让她上头”“拿捏”“测试服从度”等承诺或操控性策略。
5. 不建议故意冷落、制造嫉妒、撒谎、施压、灌醉、羞辱边界、反复试探拒绝。
6. 夸奖必须具体到“夸什么维度 + 怎么表达 + 什么场景更适合 + 哪种夸法少用”。
7. “当前处于什么阶段”和“下一步建议做什么”必须分开。current_stage/current_level 直接按现有证据判断，
   不允许因为上一轮较低就强制只升一级；强证据可以跨级，降温/撤回也可以直接回落。
8. 关系动作默认选择当前最小有效动作，但如果对方已经明确主动发起更高层级的话题或关系意图，
   可以直接承接那个已经发生的层级，不要机械要求补走中间步骤。
9. 亲密话题严格区分：话题兴趣、幻想、现实意愿、实际经历、明确边界。
10. 亲密话题 0~8 只表示“聊天话题深度”，不是关系阶段、不是 M3、也不是现实行为进度。
    current_level / next_level 可以按当前明确证据跨级或回落，但绝不能从话题深度推出现实意愿。
11. “聊得开”“开玩笑”“幻想”都不能视为现实同意。现实行为只以当下清楚、自愿、
    有能力且可撤回的同意为准。
12. 给出的示例话术必须像自然聊天骨架，不能假装知道对方没说过的事。
13. 输出严格 JSON，不要 Markdown，不要额外解释。

JSON 结构：
{
  "schema":"jev-interaction-strategy/v1",
  "summary":"一句话总策略",
  "praise":{
    "best_targets":[{"target":"夸奖方向","why":"为什么","how":"怎么夸","example":"一句自然示例","confidence":0.0,"evidence":[]}],
    "avoid":[{"item":"少用的夸法","why":"原因","evidence":[]}]
  },
  "conversation":{
    "works":[{"item":"有效聊天方式","how":"怎么做","evidence":[]}],
    "avoid":[{"item":"少用方式","why":"原因","evidence":[]}]
  },
  "emotional_support":{
    "preferred":"她难受/生气时优先怎么处理",
    "steps":["第一步","第二步"],
    "avoid":[],
    "evidence":[]
  },
  "relationship_progression":{
    "current_stage":"当前阶段或未知",
    "next_step":"下一小步",
    "examples":["自然表达骨架"],
    "advance_signals":[],
    "pause_signals":[],
    "stop_signals":[],
    "evidence":[]
  },
  "intimacy_progression":{
    "current_level":0,
    "current_name":"对应阶梯名称",
    "next_level":0,
    "next_name":"对应阶梯名称",
    "next_reason":"为什么当前可直接承接到这个层级；若回落也说明原因",
    "recommended_topics":[],
    "transition_examples":[],
    "do_not_jump_to":[],
    "advance_signals":[],
    "pause_signals":[],
    "stop_signals":[],
    "evidence":[]
  },
  "boundaries_and_risks":[{"item":"边界/风险","action":"怎么处理","evidence":[]}],
  "unknowns":["还不知道、不能推断的关键点"],
  "confidence":0.0
}
"""


def source_prompt(
    *,
    person_profile: str,
    relationship_context: str,
    intimacy_context: str,
    relationship_setting: str = "",
    notes: str = "",
    include_intimacy: bool = True,
) -> str:
    ladder = "\n".join(
        f"{x['level']} {x['name']}：{x['description']}" for x in INTIMACY_TOPIC_DEPTH
    )
    intimacy_block = (
        f"【亲密/性偏好证据】\n{intimacy_context or '暂无'}\n\n"
        "【亲密话题深度（不是关系阶段/M3）】\n" + ladder
        if include_intimacy else
        "【亲密/性偏好】本人物本次未启用，不生成亲密话题建议。"
    )
    return (
        "请根据以下已保存信息生成互动攻略。\n\n"
        f"【当前会话关系设置】\n{relationship_setting or '未知'}\n"
        f"【联系人备注】\n{notes or '无'}\n\n"
        f"【人物长期画像】\n{person_profile or '暂无'}\n\n"
        f"【关系趋势】\n{relationship_context or '暂无'}\n\n"
        + intimacy_block
    )


def _json_object(text: str) -> dict:
    raw = str(text or "").strip()
    fence = chr(96) * 3
    if raw.startswith(fence):
        lines = raw.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip().startswith(fence):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start:end + 1]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("攻略结果不是 JSON 对象")
    return data


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _text(value, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def _evidence(value) -> list[str]:
    return [_text(x, 300) for x in _list(value) if _text(x, 300)][:12]


def normalize(data: dict, *, include_intimacy: bool = True) -> dict:
    """把模型输出约束成稳定 schema；不认识的字段不进入长期策略。"""
    praise = data.get("praise") if isinstance(data.get("praise"), dict) else {}
    conversation = data.get("conversation") if isinstance(data.get("conversation"), dict) else {}
    support = data.get("emotional_support") if isinstance(data.get("emotional_support"), dict) else {}
    progress = data.get("relationship_progression") if isinstance(data.get("relationship_progression"), dict) else {}
    intimacy = data.get("intimacy_progression") if include_intimacy and isinstance(data.get("intimacy_progression"), dict) else {}

    praise_targets = []
    for x in _list(praise.get("best_targets"))[:8]:
        if not isinstance(x, dict) or not _text(x.get("target")):
            continue
        try:
            conf = max(0.0, min(1.0, float(x.get("confidence", 0.5))))
        except (TypeError, ValueError):
            conf = 0.5
        praise_targets.append({
            "target": _text(x.get("target"), 120),
            "why": _text(x.get("why"), 400),
            "how": _text(x.get("how"), 500),
            "example": _text(x.get("example"), 500),
            "confidence": conf,
            "evidence": _evidence(x.get("evidence")),
        })

    def item_list(raw, key="item", extra_key=None, max_n=10):
        out = []
        for x in _list(raw)[:max_n]:
            if not isinstance(x, dict) or not _text(x.get(key)):
                continue
            row = {key: _text(x.get(key), 300)}
            if extra_key:
                row[extra_key] = _text(x.get(extra_key), 500)
            row["evidence"] = _evidence(x.get("evidence"))
            out.append(row)
        return out

    try:
        current_level = max(0, min(8, int(intimacy.get("current_level", 0))))
    except (TypeError, ValueError):
        current_level = 0
    try:
        next_level = max(0, min(8, int(intimacy.get("next_level", current_level))))
    except (TypeError, ValueError):
        next_level = current_level

    # current_level / next_level 都是“按当前证据直接判断”的状态，不再强制相邻。
    # next_level 允许跨级承接已经明确出现的信号，也允许在降温/不适时回落。
    ladder = {x["level"]: x["name"] for x in INTIMACY_TOPIC_DEPTH}

    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError):
        confidence = 0.5

    result = {
        "schema": SCHEMA,
        "summary": _text(data.get("summary"), 600),
        "praise": {
            "best_targets": praise_targets,
            "avoid": item_list(praise.get("avoid"), "item", "why", 8),
        },
        "conversation": {
            "works": item_list(conversation.get("works"), "item", "how", 10),
            "avoid": item_list(conversation.get("avoid"), "item", "why", 10),
        },
        "emotional_support": {
            "preferred": _text(support.get("preferred"), 600),
            "steps": [_text(x, 400) for x in _list(support.get("steps")) if _text(x)][:8],
            "avoid": [_text(x, 300) for x in _list(support.get("avoid")) if _text(x)][:8],
            "evidence": _evidence(support.get("evidence")),
        },
        "relationship_progression": {
            "current_stage": _text(progress.get("current_stage"), 200) or "未知",
            "next_step": _text(progress.get("next_step"), 500),
            "examples": [_text(x, 500) for x in _list(progress.get("examples")) if _text(x)][:6],
            "advance_signals": [_text(x, 300) for x in _list(progress.get("advance_signals")) if _text(x)][:8],
            "pause_signals": [_text(x, 300) for x in _list(progress.get("pause_signals")) if _text(x)][:8],
            "stop_signals": [_text(x, 300) for x in _list(progress.get("stop_signals")) if _text(x)][:8],
            "evidence": _evidence(progress.get("evidence")),
        },
        "intimacy_progression": ({
            "current_level": current_level,
            "current_name": ladder[current_level],
            "next_level": next_level,
            "next_name": ladder[next_level],
            "next_reason": _text(intimacy.get("next_reason"), 600),
            "recommended_topics": [_text(x, 400) for x in _list(intimacy.get("recommended_topics")) if _text(x)][:8],
            "transition_examples": [_text(x, 500) for x in _list(intimacy.get("transition_examples")) if _text(x)][:6],
            "do_not_jump_to": [_text(x, 300) for x in _list(intimacy.get("do_not_jump_to")) if _text(x)][:8],
            "advance_signals": [_text(x, 300) for x in _list(intimacy.get("advance_signals")) if _text(x)][:8],
            "pause_signals": [_text(x, 300) for x in _list(intimacy.get("pause_signals")) if _text(x)][:8],
            "stop_signals": [_text(x, 300) for x in _list(intimacy.get("stop_signals")) if _text(x)][:8],
            "evidence": _evidence(intimacy.get("evidence")),
        } if include_intimacy else {}),
        "boundaries_and_risks": item_list(
            data.get("boundaries_and_risks"), "item", "action", 12
        ),
        "unknowns": [_text(x, 300) for x in _list(data.get("unknowns")) if _text(x)][:12],
        "confidence": confidence,
    }
    return result


def generate(
    *,
    person_profile: str,
    relationship_context: str,
    intimacy_context: str,
    relationship_setting: str,
    notes: str,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str,
    thinking: bool = False,
    timeout: float = 120,
    include_intimacy: bool = True,
) -> dict:
    spec = providers.DRAFT_PROVIDERS[provider]
    prompt = source_prompt(
        person_profile=person_profile,
        relationship_context=relationship_context,
        intimacy_context=intimacy_context,
        relationship_setting=relationship_setting,
        notes=notes,
        include_intimacy=include_intimacy,
    )
    content = llm.chat(
        spec.protocol,
        base_url or spec.base,
        api_key,
        model or spec.default,
        SYSTEM,
        [prompt],
        temperature=0.15,
        max_tokens=6500 if thinking else 4500,
        thinking=thinking,
        extra_body=spec.extra(thinking),
        headers=spec.headers,
        timeout=timeout,
    )
    return normalize(_json_object(content), include_intimacy=include_intimacy)


def profile_source_id(profile: dict) -> str:
    raw = json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha1(raw.encode("utf-8")).hexdigest()[:24]


def context_text(profile: dict, *, include_intimacy: bool = False) -> str:
    """给实时 Jev 的短版策略，不把整份攻略每轮全塞进去。"""
    if not isinstance(profile, dict) or not profile:
        return ""

    lines = ["【这个人的互动攻略】"]
    if profile.get("summary"):
        lines.append("- 总体：" + str(profile["summary"]))

    praise = ((profile.get("praise") or {}).get("best_targets") or [])[:3]
    if praise:
        lines.append("- 夸奖优先：" + "；".join(
            f"{x.get('target','')}（{x.get('how','')}）" for x in praise if isinstance(x, dict)
        ))

    conv = ((profile.get("conversation") or {}).get("works") or [])[:3]
    if conv:
        lines.append("- 聊天方式：" + "；".join(
            str(x.get("item") or "") for x in conv if isinstance(x, dict)
        ))

    progress = profile.get("relationship_progression") or {}
    if progress.get("next_step"):
        lines.append("- 关系下一步：" + str(progress["next_step"]))

    intimacy = profile.get("intimacy_progression") or {}
    if include_intimacy and intimacy:
        lines.append(
            f"- 亲密话题深度：当前 {intimacy.get('current_level',0)}级 "
            f"{intimacy.get('current_name','')}；当前可承接到 "
            f"{intimacy.get('next_level',0)}级 {intimacy.get('next_name','')}"
        )
        topics = intimacy.get("recommended_topics") or []
        if topics:
            lines.append("- 当前可聊：" + "；".join(str(x) for x in topics[:4]))

    risks = profile.get("boundaries_and_risks") or []
    if include_intimacy and risks:
        lines.append("- 边界：" + "；".join(
            str(x.get("item") or "") for x in risks[:4] if isinstance(x, dict)
        ))
    return "\n".join(lines)
