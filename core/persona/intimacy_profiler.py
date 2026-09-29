# -*- coding: utf-8 -*-
"""从聊天批次生成“亲密/性偏好”候选画像，并写入长期记忆。"""
from __future__ import annotations

import json
from hashlib import sha1

from app import relationship_memory
from core import llm, providers
from core.persona import intimacy_atlas

_ALLOWED_SCOPES = {
    "topic_interest", "fantasy", "real_world_willingness", "experience", "boundary",
}
_ALLOWED_CERTAINTY = {"explicit", "inferred"}

SYSTEM = """你是 Jev 的敏感亲密画像分析器。输入是某个成年人目标对象的聊天记录。
目标是发现长期稳定或明确表达的亲密/性偏好、角色倾向和边界，不做医学或精神诊断。

硬规则：
1. 只分析目标对象本人的表达和反应；“我”说了什么只能当上下文，不能替目标对象表态。
2. 一次玩笑、一次转发、一次好奇、一次没有明确回应的暧昧话题，不足以建立长期画像。
3. 普通性格强势不能直接推出性方面偏主导；自卑不能直接推出偏顺从或受虐。
4. topic_interest / fantasy / real_world_willingness / experience / boundary 必须分开。
5. 幻想不等于现实愿意；现实愿意不等于实际经历；任何现实行为都不能从幻想自动升级。
6. explicit 仅用于目标对象明确说过或明确确认过的内容；其余只能 inferred。
7. inferred 必须有重复或跨时间证据。证据不足就不要输出。
8. 必须保留反证；出现明显冲突时降低 confidence，不要强行统一。
9. 不因为某个标签常见就补全其他标签；未知就是未知。
10. 输出严格 JSON，不要 Markdown，不要解释。

输出：
{"findings":[{"dimension":"自由文本或现有术语","value":"简短结论","scope":"topic_interest|fantasy|real_world_willingness|experience|boundary","certainty":"explicit|inferred","confidence":0.0,"evidence_ids":["消息ID"],"counterevidence_ids":["消息ID"]}]}
"""


def _message_line(item: dict, index: int) -> str:
    mid = str(item.get("id") or item.get("messageRef") or item.get("msg_id") or f"row-{index}")
    who = item.get("from")
    if who not in {"her", "me"}:
        direction = str(item.get("direction") or "")
        is_sender = item.get("isSender")
        who = "me" if is_sender is True or direction == "to_target" else "her"
    text = str(item.get("text") or item.get("content") or "").strip()
    when = item.get("datetime") or item.get("timestamp") or item.get("createTime") or ""
    return f"[{mid}] [{when}] {who}: {text}"


def build_prompt(messages: list[dict]) -> str:
    lines = [_message_line(x if isinstance(x, dict) else {}, i) for i, x in enumerate(messages)]
    lines = [x for x in lines if x.rsplit(": ", 1)[-1].strip()]
    return (
        "请分析下面这一批聊天。优先使用已有性癖/关系角色术语，但不要为了匹配目录而硬贴标签。\n"
        "对每条 finding 给出原始消息 ID 作为证据。\n\n"
        "<<<聊天批次>>>\n" + "\n".join(lines) + "\n<<<结束>>>"
    )


def _extract_json(text: str) -> dict:
    text = str(text or "").strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith(fence):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("画像分析结果不是 JSON 对象")
    return data


def normalize_findings(data: dict) -> list[dict]:
    out: list[dict] = []
    for raw in data.get("findings") or []:
        if not isinstance(raw, dict):
            continue
        dimension = str(raw.get("dimension") or "").strip()
        value = str(raw.get("value") or "").strip()
        scope = str(raw.get("scope") or "").strip()
        certainty = str(raw.get("certainty") or "").strip()
        if not dimension or not value or scope not in _ALLOWED_SCOPES or certainty not in _ALLOWED_CERTAINTY:
            continue

        try:
            confidence = max(0.0, min(1.0, float(raw.get("confidence", 0))))
        except (TypeError, ValueError):
            continue

        evidence_ids = [str(x) for x in (raw.get("evidence_ids") or []) if str(x).strip()]
        counter_ids = [str(x) for x in (raw.get("counterevidence_ids") or []) if str(x).strip()]

        if certainty == "inferred":
            if len(set(evidence_ids)) < 2:
                continue
            confidence = min(confidence, 0.75)
            if scope in {"real_world_willingness", "experience", "boundary"}:
                confidence = min(confidence, 0.60)

        canonical = intimacy_atlas.canonicalize(
            dimension, kinds={"kink", "role", "relationship"}
        )
        source_id = sha1(
            ("|".join([
                str(canonical["id"]), value, scope, certainty,
                *sorted(set(evidence_ids)),
            ])).encode("utf-8")
        ).hexdigest()[:24]

        out.append({
            "dimension": canonical.get("label") or dimension,
            "canonical_id": canonical.get("id"),
            "canonical_source": canonical.get("source"),
            "value": value,
            "scope": scope,
            "certainty": certainty,
            "confidence": confidence,
            "evidence_ids": evidence_ids,
            "counterevidence_ids": counter_ids,
            "source_id": source_id,
        })
    return out


def store_findings(
    person_id: str,
    findings: list[dict],
    *,
    source_type: str = "history-profile",
) -> list[int]:
    if not relationship_memory.learning_enabled(person_id):
        return []

    ids: list[int] = []
    for item in findings:
        evidence = "消息证据：" + ", ".join(item.get("evidence_ids") or [])
        counter = "反证：" + ", ".join(item.get("counterevidence_ids") or [])
        ids.append(relationship_memory.add_intimacy_preference(
            person_id,
            str(item["dimension"]),
            str(item["value"]),
            scope=str(item["scope"]),
            certainty=str(item["certainty"]),
            confidence=float(item["confidence"]),
            source_type=source_type,
            source_id=str(item["source_id"]),
            evidence=evidence,
            counterevidence=counter,
        ))
    return ids


def analyze_batch(
    person_id: str,
    messages: list[dict],
    *,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str,
    thinking: bool = False,
    timeout: float = 90,
) -> list[dict]:
    if not relationship_memory.learning_enabled(person_id):
        return []

    spec = providers.DRAFT_PROVIDERS[provider]
    content = llm.chat(
        spec.protocol,
        base_url or spec.base,
        api_key,
        model or spec.default,
        SYSTEM,
        [build_prompt(messages)],
        temperature=0.1,
        max_tokens=5000 if thinking else 3000,
        thinking=thinking,
        extra_body=spec.extra(thinking),
        headers=spec.headers,
        timeout=timeout,
    )
    findings = normalize_findings(_extract_json(content))
    store_findings(person_id, findings)
    return findings


def analyze_history(
    person_id: str,
    messages: list[dict],
    *,
    provider: str,
    model: str,
    base_url: str | None,
    api_key: str,
    thinking: bool = False,
    batch_size: int = 180,
) -> list[dict]:
    """100~300 条一批处理，避免一条消息调用一次模型。"""
    size = max(100, min(300, int(batch_size)))
    out: list[dict] = []
    for i in range(0, len(messages), size):
        batch = messages[i:i + size]
        if batch:
            out.extend(analyze_batch(
                person_id,
                batch,
                provider=provider,
                model=model,
                base_url=base_url,
                api_key=api_key,
                thinking=thinking,
            ))
    return out
