# -*- coding: utf-8 -*-
from core.persona import intimacy_atlas
from core.persona import intimacy_profiler


def test_intimacy_atlas_loads_all_source_layers():
    cov = intimacy_atlas.coverage()
    assert cov["kinkdirectory_kinks"] >= 170
    assert cov["klist_kinks"] >= 150
    assert cov["relationship_terms"] >= 150
    assert cov["role_terms"] >= 1000
    assert cov["kinkxknow_archetypes"] >= 10
    assert cov["kos_meta_dimensions"] == 5


def test_intimacy_atlas_can_find_chinese_kink_label():
    hits = intimacy_atlas.search("乳胶", kinds={"kink"})
    assert hits
    assert hits[0]["kind"] == "kink"


def test_intimacy_atlas_does_not_force_unknown_term():
    item = intimacy_atlas.canonicalize("这是一个完全不存在的自定义偏好")
    assert item["source"] == "jev"
    assert item["kind"] == "custom"


def test_kinkxknow_role_scoring_is_deterministic():
    scores = intimacy_atlas.archetype_scores({
        "contract": 10,
        "tasking": 10,
        "impact": 10,
        "feedback": 10,
    }, evidence_type="questionnaire")
    assert scores["Disciplinarian"] == 100.0
    assert 0 <= scores["Dominant"] <= 100


def test_profiler_requires_repeated_evidence_for_inference():
    got = intimacy_profiler.normalize_findings({
        "findings": [{
            "dimension": "乳胶",
            "value": "可能喜欢",
            "scope": "fantasy",
            "certainty": "inferred",
            "confidence": 0.9,
            "evidence_ids": ["m1"],
        }]
    })
    assert got == []


def test_profiler_keeps_explicit_and_canonicalizes():
    got = intimacy_profiler.normalize_findings({
        "findings": [{
            "dimension": "乳胶",
            "value": "明确说喜欢",
            "scope": "topic_interest",
            "certainty": "explicit",
            "confidence": 1.0,
            "evidence_ids": ["m1"],
        }]
    })
    assert len(got) == 1
    assert got[0]["canonical_source"] == "kinkdirectory"
    assert got[0]["confidence"] == 1.0


def test_kinkxknow_rejects_chat_inferred_scores():
    import pytest
    with pytest.raises(ValueError):
        intimacy_atlas.archetype_scores({"contract": 8})


def test_canonicalize_does_not_fuzzy_merge_neighboring_terms():
    # search 可以做模糊查找，但正式 canonicalize 只允许精确 ID/标签命中。
    item = intimacy_atlas.canonicalize("乳胶相关但不是原标签")
    assert item["source"] == "jev"
    assert item["kind"] == "custom"
