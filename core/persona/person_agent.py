# -*- coding: utf-8 -*-
"""人物分析 Agent：允许用户直接把观察、原话、粘贴聊天和任意平台资料喂给 Jev。

它不依赖微信，也不要求先有聊天记录。原始输入先落本地 source_items，
模型只负责从该输入中提取候选画像；所有推断都保留来源。
"""
from __future__ import annotations

import json
from hashlib import sha1

from app import relationship_memory
from core import llm, providers
from core.sources.models import SOURCE_KINDS

_MEMORY_KINDS = {
    "like", "dislike", "boundary", "habit", "event",
    "promise", "profile", "communication",
}
_SCOPES = {
    "topic_interest", "fantasy", "real_world_willingness", "experience", "boundary",
}

SYSTEM = """你是 Jev 的人物分析 Agent。用户会输入他对某个成年人的观察、对方原话、
粘贴聊天或来自任意平台的资料。你的任务是：
1. 回应用户当前描述；
2. 只提取有证据的人物事实/推测；
3. 需要时提出最多两个后续问题，帮助完善人物画像；
4. 不因为缺少聊天记录而拒绝分析。

重要区分：
- 用户自己的观察 != 对方明确承认的事实。
- source_kind=observation/note 只作为用户观察，certainty 只能 inferred；如果是对方明确原话，应由用户选择 target_statement。
- target_statement 是用户录入的对方明确原话，可以提取 explicit。
- chat_paste/platform_import 中，只能把对方直接表达的内容作为 explicit；从行为模式推断的仍是 inferred。
- source_kind=agent_chat 时，只回答用户的问题或讨论已有画像，不把本轮文字当作新证据。
- 不做医学或精神诊断。用“可能/倾向/目前证据”描述推测。
- 普通人格特征不能自动推出性偏好。
- 亲密/性话题必须区分：话题兴趣、幻想、现实意愿、实际经历、明确边界。
- 幻想不等于现实愿意，现实愿意不等于实际经历。
- 不把用户希望发生的事当成对方意愿。
- 如果当前信息不足，明确说还不知道，不为了填满画像而猜。

输出严格 JSON：
{
  "reply":"给用户的自然中文回复，说明本轮看到了什么、还缺什么",
  "memories":[
    {"kind":"like|dislike|boundary|habit|event|promise|profile|communication",
     "content":"简短结论","certainty":"explicit|inferred","confidence":0.0,
     "evidence":"本次输入中支持它的具体内容"}
  ],
  "intimacy":[
    {"dimension":"具体亲密/性偏好维度","value":"简短结论",
     "scope":"topic_interest|fantasy|real_world_willingness|experience|boundary",
     "certainty":"explicit|inferred","confidence":0.0,
     "evidence":"本次输入证据","counterevidence":"如有反证"}
  ],
  "questions":["最多两个真正有用的后续问题"]
}
"""


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
        raise ValueError("人物分析结果不是 JSON 对象")
    return data


def _confidence(value, default=0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _normalize(data: dict, source_kind: str) -> dict:
    allow_explicit = source_kind in {"target_statement", "chat_paste", "platform_import"}

    memories = []
    if source_kind == "agent_chat":
        data = dict(data)
        data["memories"] = []
        data["intimacy"] = []
    for raw in data.get("memories") or []:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "").strip()
        content = str(raw.get("content") or "").strip()
        certainty = str(raw.get("certainty") or "inferred").strip()
        if kind not in _MEMORY_KINDS or not content:
            continue
        if certainty not in {"explicit", "inferred"}:
            certainty = "inferred"
        if certainty == "explicit" and not allow_explicit:
            certainty = "inferred"
        conf = _confidence(raw.get("confidence"))
        if certainty == "inferred":
            conf = min(conf, 0.75 if source_kind in {"observation", "note"} else 0.85)
        memories.append({
            "kind": kind,
            "content": content[:800],
            "certainty": certainty,
            "confidence": conf,
            "evidence": str(raw.get("evidence") or "").strip()[:1200],
        })

    intimacy = []
    for raw in data.get("intimacy") or []:
        if not isinstance(raw, dict):
            continue
        dimension = str(raw.get("dimension") or "").strip()
        value = str(raw.get("value") or "").strip()
        scope = str(raw.get("scope") or "").strip()
        certainty = str(raw.get("certainty") or "inferred").strip()
        if not dimension or not value or scope not in _SCOPES:
            continue
        if certainty not in {"explicit", "inferred"}:
            certainty = "inferred"
        if certainty == "explicit" and not allow_explicit:
            certainty = "inferred"

        conf = _confidence(raw.get("confidence"))
        if certainty == "inferred":
            conf = min(conf, 0.65)
            if source_kind in {"observation", "note"}:
                conf = min(conf, 0.55)
            if scope in {"real_world_willingness", "experience", "boundary"}:
                conf = min(conf, 0.50)

        intimacy.append({
            "dimension": dimension[:240],
            "value": value[:800],
            "scope": scope,
            "certainty": certainty,
            "confidence": conf,
            "evidence": str(raw.get("evidence") or "").strip()[:1200],
            "counterevidence": str(raw.get("counterevidence") or "").strip()[:1200],
        })

    questions = [
        str(x).strip()[:500]
        for x in (data.get("questions") or [])
        if str(x).strip()
    ][:2]
    return {
        "reply": str(data.get("reply") or "").strip()[:3000],
        "memories": memories[:24],
        "intimacy": intimacy[:20],
        "questions": questions,
    }


def analyze_input(
    *,
    person_id: str,
    text: str,
    source_kind: str,
    platform: str,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str,
    thinking: bool = False,
    relationship: str = "",
    timeout: float = 120,
) -> dict:
    """保存原始输入 -> Agent 分析 -> 保存结构化人物记忆 -> 保存 Agent 回复。"""
    person_id = str(person_id or "").strip()
    text = str(text or "").strip()
    if not person_id or not text:
        raise ValueError("人物和输入内容不能为空")
    if source_kind not in SOURCE_KINDS:
        raise ValueError("资料类型无效")

    source_id = relationship_memory.add_source_item(
        person_id,
        text,
        source_kind=source_kind,
        platform=platform,
        author_role="observer" if source_kind in {"observation", "note"} else "source",
    )
    relationship_memory.add_dialogue_entry(
        person_id, "user", text, source_item_id=source_id
    )

    existing = relationship_memory.memory_context(person_id, include_intimacy=False)
    recent_dialogue = relationship_memory.dialogue(person_id, limit=12)
    dialogue_text = "\n".join(
        ("用户" if x["role"] == "user" else "Agent") + "：" + str(x["content"])
        for x in recent_dialogue[:-1]
    )[-6000:]

    prompt = (
        f"人物ID：{person_id}\n"
        f"当前关系：{relationship or '未知'}\n"
        f"资料类型：{source_kind}\n"
        f"来源平台：{platform}\n\n"
        f"【已有长期画像】\n{existing or '暂无'}\n\n"
        f"【最近人物分析对话】\n{dialogue_text or '暂无'}\n\n"
        f"【用户本轮输入】\n{text}"
    )

    spec = providers.DRAFT_PROVIDERS[provider]
    raw = llm.chat(
        spec.protocol,
        base_url or spec.base,
        api_key,
        model or spec.default,
        SYSTEM,
        [prompt],
        temperature=0.1,
        max_tokens=5000 if thinking else 3500,
        thinking=thinking,
        extra_body=spec.extra(thinking),
        headers=spec.headers,
        timeout=timeout,
    )
    result = _normalize(_json_object(raw), source_kind)

    source_ref = f"source-item:{source_id}"
    stored_memory_ids = []
    for item in result["memories"]:
        mid = relationship_memory.remember(
            person_id,
            item["kind"],
            item["content"],
            confidence=item["confidence"],
            source_type="person-agent",
            source_id=source_ref + ":" + sha1(
                (item["kind"] + "|" + item["content"]).encode("utf-8")
            ).hexdigest()[:12],
            evidence=(f"原始资料 #{source_id}：" + item["evidence"]).strip(),
            certainty=item["certainty"],
        )
        stored_memory_ids.append(mid)

    stored_intimacy_ids = []
    for item in result["intimacy"]:
        iid = relationship_memory.add_intimacy_preference(
            person_id,
            item["dimension"],
            item["value"],
            scope=item["scope"],
            certainty=item["certainty"],
            confidence=item["confidence"],
            source_type="person-agent",
            source_id=source_ref + ":" + sha1(
                (item["dimension"] + "|" + item["value"] + "|" + item["scope"]).encode("utf-8")
            ).hexdigest()[:12],
            evidence=(f"原始资料 #{source_id}：" + item["evidence"]).strip(),
            counterevidence=item["counterevidence"],
        )
        stored_intimacy_ids.append(iid)

    reply = result["reply"]
    if result["questions"]:
        reply = (reply + "\n\n还可以继续补充：\n- " + "\n- ".join(result["questions"])).strip()
    if not reply:
        reply = f"已记录这条资料。本轮提取 {len(stored_memory_ids)} 条人物信息。"
    relationship_memory.add_dialogue_entry(person_id, "assistant", reply)

    result["source_item_id"] = source_id
    result["stored_memory_ids"] = stored_memory_ids
    result["stored_intimacy_ids"] = stored_intimacy_ids
    result["reply"] = reply
    return result
