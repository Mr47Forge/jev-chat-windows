# -*- coding: utf-8 -*-
from core import reply_logic


def test_reply_logic_detects_ioi_from_multiple_observable_signals():
    got = reply_logic.build({
        "partner_tone": {"choice": "playful", "confidence": 0.8},
        "interaction_trend": {"choice": "warming", "confidence": 0.7},
        "reciprocity": {"choice": "balanced", "confidence": 0.8},
        "love_action": {"choice": "flirt_lightly", "confidence": 0.75},
        "she_needs": {"choice": "nothing"},
    }, "你还挺会接梗")

    terms = {x["term"] for x in got["terms"]}
    assert "IOI" in terms
    assert "Push-Pull" in terms
    assert got["energy"]["interaction_tension"] == "略升"
    assert got["energy"]["target_self_worth"] == "不作为调整目标"


def test_reply_logic_detects_iod_from_trend_not_one_short_reply():
    got = reply_logic.build({
        "partner_tone": {"choice": "withdrawing"},
        "interaction_trend": {"choice": "cooling", "confidence": 0.85},
        "reciprocity": {"choice": "user_more"},
        "love_action": {"choice": "give_space"},
    }, "行 你忙")

    terms = {x["term"] for x in got["terms"]}
    assert "IOD" in terms
    assert got["energy"]["interaction_tension"] == "降低"
    assert got["energy"]["user_investment"] == "降低"


def test_one_positive_signal_alone_is_not_ioi():
    got = reply_logic.build({
        "partner_tone": {"choice": "warm"},
        "interaction_trend": {"choice": "insufficient"},
        "reciprocity": {"choice": "insufficient"},
        "love_action": {"choice": "respond_lightly"},
    }, "哈哈")
    assert "IOI" not in {x["term"] for x in got["terms"]}


def test_reply_logic_render_contains_why_and_energy_breakdown():
    got = reply_logic.build({
        "partner_tone": {"choice": "testing"},
        "true_intent": {"choice": "confirm_you_care", "confidence": 0.9},
        "she_needs": {"choice": "care"},
        "love_action": {"choice": "show_care"},
    }, "我记得")
    text = reply_logic.render_text(got)
    assert "Frame" in text
    assert "为什么这样回" in text
    assert "所谓“能级”拆开看" in text
    assert "对方自尊：不作为调整目标" in text
