# -*- coding: utf-8 -*-
"""Regression tests for the relationship decision loop. No network calls."""
from unittest.mock import patch

from core.engine import analyze


def test_check_history_requests_real_history_instead_of_fake_ocr_expansion():
    messages = [("her" if i % 2 == 0 else "me", f"当前窗口消息{i}") for i in range(17)]

    judged = {"answers": {
        "best_action": {"choice": "check_history"},
        "love_action": {"choice": "check_history"},
        "she_needs": {"choice": "care"},
    }, "usage": {}}
    ranked = {"answers": {"best_reply": {
        "choice": "reply_a",
        "probabilities": {"reply_a": 0.8, "reply_b": 0.15, "reply_c": 0.05},
    }}, "usage": {}}

    with patch("core.engine.ask", side_effect=[judged, ranked]) as mocked_ask, \
         patch("core.engine.draft_candidates", return_value=["先核对一下", "我记得", "等我一下"]):
        result = analyze(messages, "partner", context=10)

    assert result["history_requested"] is True
    assert result["history_checked"] is False
    assert result["history_context"] == 10
    assert len(mocked_ask.call_args_list[0].args[0]["chat"]["messages"]) == 10
    assert len(mocked_ask.call_args_list) == 2

def test_resolved_conversation_sets_stop_flag():
    answers = {
        "true_intent": {"choice": "close_topic"},
        "she_needs": {"choice": "nothing"},
        "tension_resolved": {"noul": 0.94},
        "best_action": {"choice": "say_less"},
    }
    ranked = {"answers": {"best_reply": {
        "choice": "reply_a",
        "probabilities": {"reply_a": 0.9, "reply_b": 0.08, "reply_c": 0.02},
    }}, "usage": {}}

    with patch("core.engine.ask", side_effect=[{"answers": answers, "usage": {}}, ranked]), \
         patch("core.engine.draft_candidates", return_value=["好", "嗯好", "知道啦"]):
        result = analyze([("her", "这还差不多")], "partner", context=10)

    assert result["stop_analysis"] is True
    assert result["history_checked"] is False
