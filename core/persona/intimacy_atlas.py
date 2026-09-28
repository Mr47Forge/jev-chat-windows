# -*- coding: utf-8 -*-
"""Jev 自用的亲密/性偏好综合图谱。

多个现成项目只提供目录、角色和评分结构，不直接决定人物结论。
真正的人物画像仍必须由聊天证据 + certainty/confidence 决定。
"""
from __future__ import annotations

import csv
import html
import json
import re
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_VENDOR = _ROOT / "vendor" / "intimacy_sources"

KINKXKNOW_TRAIT_WEIGHTS: dict[str, dict[str, int]] = {
    "Submissive": {"safeword": 1, "vulnerability": 2, "contract": 1, "autonomy": 1},
    "Brat": {"autonomy": -1, "humiliation": 1, "impact": 1, "feedback": -1},
    "Little": {"vulnerability": 2, "aftercare": 2, "medical": 1},
    "Pet": {"public_ack": 2, "collaring": 2, "ownership": 2, "bondage": 1},
    "Rope Bunny": {"bondage": 2, "sensory_deprivation": 2, "temp_play": 1},
    "Dominant": {"contract": 2, "autonomy": -1, "tasking": 1},
    "Nurturer": {"safeword": 2, "vulnerability": 1, "checkin": 2, "aftercare": 2},
    "Master": {"contract": 2, "dynamic_type": 2, "ownership": 2, "collaring": 2},
    "Rigger": {"bondage": 2, "sensory_deprivation": 1, "temp_play": 1},
    "Caretaker": {"checkin": 2, "aftercare": 2, "medical": 1},
    "Disciplinarian": {"contract": 2, "tasking": 2, "impact": 2, "feedback": 2},
}

KOS_META_DIMENSIONS = {
    "identity": "性癖身份认同",
    "practice": "实际实践",
    "paraphernalia": "相关物品/装备",
    "community": "社群参与",
    "sexual_communication": "性与亲密沟通",
}


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(text or "").casefold())


@lru_cache(maxsize=1)
def source_versions() -> dict:
    # 新版完整同步器统一把实际 SHA 写到 vendor/UPSTREAMS.lock.json。
    path = _ROOT / "vendor" / "UPSTREAMS.lock.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        sources = data.get("sources") if isinstance(data, dict) else None
        if isinstance(sources, dict):
            return sources
    except (OSError, ValueError):
        pass

    # 兼容完整同步器第一次运行前的旧快照。
    legacy = _VENDOR / "UPSTREAM.json"
    try:
        return json.loads(legacy.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=1)
def kink_entries() -> list[dict]:
    path = _VENDOR / "kinkdirectory" / "src" / "locales-csv" / "kink-translations-zh.csv"
    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            kink_id = str(row.get("Kink ID") or "").strip()
            if not kink_id:
                continue
            rows.append({
                "kind": "kink",
                "source": "kinkdirectory",
                "id": kink_id,
                "category_id": str(row.get("Category ID") or "").strip(),
                "category": str(row.get("Category Name") or "").strip(),
                "label": str(row.get("Label") or kink_id).strip(),
                "description": str(row.get("Tooltip") or "").strip(),
            })
    return rows


@lru_cache(maxsize=1)
def relationship_atlas() -> dict:
    path = _VENDOR / "relationship-atlas" / "src" / "data" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    relationship_fields = data.get("relationshipFields") or []
    role_fields = data.get("roleFields") or []

    relationships = []
    for row in data.get("relationships") or []:
        item = dict(zip(relationship_fields, row))
        relationships.append({
            "kind": "relationship",
            "source": "relationship-atlas",
            "id": _norm(item.get("Relationship term", "")),
            "label": item.get("Relationship term", ""),
            "category": item.get("Classification", ""),
            "partner_label": item.get("Partner-side label", ""),
            "pairing_confidence": item.get("Pairing confidence", ""),
            "source_url": item.get("Source", ""),
        })

    roles = []
    for row in data.get("roles") or []:
        item = dict(zip(role_fields, row))
        roles.append({
            "kind": "role",
            "source": "relationship-atlas",
            "id": _norm(item.get("Role", "")),
            "label": item.get("Role", ""),
            "category": item.get("FetLife category", ""),
            "authority_axis": item.get("Authority axis", ""),
            "activity_axis": item.get("Activity axis", ""),
            "relationship_role_axis": item.get("Relationship-role axis", ""),
            "partner_label": item.get("Partner-side label", ""),
            "source_url": item.get("Source", ""),
        })
    return {"meta": data.get("meta") or {}, "relationships": relationships, "roles": roles}


def _parse_klist_data(data: str, variant: str) -> list[dict]:
    category = ""
    columns: list[str] = []
    out: list[dict] = []
    seen: set[tuple] = set()
    for line in data.splitlines():
        line = line.strip()
        if line.startswith("#"):
            category = line[1:].strip()
            columns = []
        elif line.startswith("(") and line.endswith(")"):
            columns = [x.strip() for x in line[1:-1].replace("/", ",").split(",") if x.strip()]
        elif line.startswith("* "):
            label = line[2:].strip()
            if not label:
                continue
            key = (_norm(category), _norm(label), tuple(_norm(x) for x in columns))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "kind": "kink",
                "source": "klist",
                "source_variant": variant,
                "id": _norm(label),
                "category": category,
                "label": label,
                "perspectives": list(columns),
            })
    return out


def _extract_klist_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".js":
        match = re.search(r'\bdata:\s*"((?:\\.|[^"\\])*)"', text, flags=re.S)
        if not match:
            return ""
        try:
            return json.loads('"' + match.group(1) + '"')
        except ValueError:
            return ""

    match = re.search(
        r'<textarea[^>]+id=["\']Kinks["\'][^>]*>(.*?)</textarea>',
        text,
        flags=re.I | re.S,
    )
    return html.unescape(match.group(1)) if match else ""


@lru_cache(maxsize=1)
def klist_entries() -> list[dict]:
    """把 KList 当前版和较新的历史大表都纳入长尾词典。

    KList 不同版本的数据规模差异很大；只读根目录 script.js 会漏掉 v2.x 中的大量项目。
    因此保留上游完整仓库后，从多个已发布版本合并，且保留 source_variant 追溯来源。
    """
    root = _VENDOR / "klist"
    candidates = [
        ("v2.01", root / "v2.01.html"),
        ("v2.0", root / "v2.0.html"),
        ("v1.1.1", root / "v1.1.1.html"),
        ("current-script", root / "script.js"),
    ]
    merged: list[dict] = []
    seen: set[tuple] = set()
    for variant, path in candidates:
        if not path.exists():
            continue
        for item in _parse_klist_data(_extract_klist_text(path), variant):
            key = (
                _norm(item.get("category", "")),
                _norm(item.get("label", "")),
                tuple(_norm(x) for x in item.get("perspectives", [])),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


@lru_cache(maxsize=1)
def unified_terms() -> list[dict]:
    atlas = relationship_atlas()
    return kink_entries() + klist_entries() + atlas["roles"] + atlas["relationships"]


def search(query: str, *, kinds: set[str] | None = None, limit: int = 20) -> list[dict]:
    q = _norm(query)
    if not q:
        return []

    ranked = []
    for item in unified_terms():
        if kinds and item.get("kind") not in kinds:
            continue
        label = _norm(item.get("label", ""))
        ident = _norm(item.get("id", ""))
        desc = _norm(item.get("description", ""))
        if q == label or q == ident:
            score = 100
        elif q in label or label in q:
            score = 80
        elif q in desc:
            score = 55
        else:
            continue
        ranked.append((score, item))

    ranked.sort(key=lambda x: (-x[0], str(x[1].get("label", ""))))
    return [dict(item) for _, item in ranked[:max(1, int(limit))]]


def canonicalize(raw: str, *, kinds: set[str] | None = None) -> dict:
    hits = search(raw, kinds=kinds, limit=1)
    if hits:
        return hits[0]
    return {
        "kind": "custom",
        "source": "jev",
        "id": "custom:" + (_norm(raw) or "unknown"),
        "label": str(raw or "").strip(),
    }


def archetype_scores(features: dict[str, float | int]) -> dict[str, float]:
    """按 KinkXKnow 的权重结构计算角色倾向。

    features 是 0~10 的证据强度，不等于诊断分数。
    """
    clean: dict[str, float] = {}
    for key, value in (features or {}).items():
        try:
            clean[str(key)] = max(0.0, min(10.0, float(value)))
        except (TypeError, ValueError):
            continue

    out: dict[str, float] = {}
    for role, weights in KINKXKNOW_TRAIT_WEIGHTS.items():
        points = sum(clean.get(key, 0.0) * weight for key, weight in weights.items())
        total = sum(abs(weight) * 10.0 for weight in weights.values())
        out[role] = max(0.0, min(100.0, (points / total * 100.0) if total else 0.0))
    return out


def coverage() -> dict:
    atlas = relationship_atlas()
    return {
        "kinkdirectory_kinks": len(kink_entries()),
        "klist_kinks": len(klist_entries()),
        "relationship_terms": len(atlas["relationships"]),
        "role_terms": len(atlas["roles"]),
        "kinkxknow_archetypes": len(KINKXKNOW_TRAIT_WEIGHTS),
        "kos_meta_dimensions": len(KOS_META_DIMENSIONS),
        "sources": source_versions(),
    }
