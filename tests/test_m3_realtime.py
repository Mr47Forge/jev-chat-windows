# -*- coding: utf-8 -*-
from core.love_questions import LOVE_CHOICE_LABELS, LOVE_QUESTIONS, LOVE_GUIDE_FIELDS
from core import reply_logic


def test_m3_question_allows_direct_phase_jump():
    question = LOVE_QUESTIONS["m3_phase"]
    text = question["instructions"]
    assert "Do not force adjacency" in text
    assert set(question["criteria"]) == {
        "insufficient", "A1", "A2", "A3", "C1", "C2", "C3", "S1", "S2", "S3"
    }


def test_relationship_stage_is_not_an_adjacency_ladder():
    text = LOVE_QUESTIONS["relationship_stage"]["instructions"]
    assert "NOT an adjacency ladder" in text
    assert "serious explicit relationship/commitment proposal" in text


def test_m3_is_visible_in_labels_and_guidance_fields():
    assert LOVE_CHOICE_LABELS["m3_phase"]["A3"].startswith("A3")
    assert all(name != "m3_phase" for name, _ in LOVE_GUIDE_FIELDS)


def test_reply_logic_explains_phase_is_direct_not_plus_one():
    got = reply_logic.build({
        "m3_phase": {"choice": "C2", "confidence": 0.9},
        "relationship_stage": {"choice": "pre_commitment"},
        "partner_tone": {"choice": "warm"},
        "interaction_trend": {"choice": "warming"},
        "reciprocity": {"choice": "partner_more"},
        "interaction_task": {"choice": "build_connection"},
        "best_action": {"choice": "acknowledge"},
    }, "我也认真想过我们以后")
    assert got["m3_phase"] == "C2"
    rendered = reply_logic.render_text(got)
    assert "C2" in rendered
    assert "仅用于理解原体系" in rendered
    assert "本轮主动作是接住当前表达" in rendered
