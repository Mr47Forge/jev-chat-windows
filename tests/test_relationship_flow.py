# -*- coding: utf-8 -*-
"""Regression tests for the relationship decision loop. No network calls."""
from unittest.mock import patch

from core.engine import analyze


def test_check_history_expands_context_before_drafting():
    messages = []
    for i in range(14):
        messages.append(("me" if i % 2 else "her", f"旧消息{i}"))
    messages += [
        ("her", "你今天是不是又忘了我跟你说过什么？"),
        ("me", "记得，你先别提示我，让我自己说"),
        ("her", "那你说"),
    ]

    replies = [
        {"answers": {
            "best_action": {"choice": "check_history"},
            "love_action": {"choice": "check_history"},
            "she_needs": {"choice": "care"},
        }, "usage": {}},
        {"answers": {
            "best_action": {"choice": "make_plan"},
            "love_action": {"choice": "repair"},
            "she_needs": {"choice": "action"},
            "tension_resolved": {"noul": 0.1},
        }, "usage": {}},
        {"answers": {"best_reply": {
            "choice": "reply_a",
            "probabilities": {"reply_a": 0.8, "reply_b": 0.15, "reply_c": 0.05},
        }}, "usage": {}},
    ]

    with patch("core.engine.ask", side_effect=replies) as mocked_ask, \
         patch("core.engine.draft_candidates", return_value=["我记得，周末吃饭我来把时间地点定好", "我来安排", "这次我弄好"]):
        result = analyze(messages, "partner", context=10)

    assert result["history_checked"] is True
    assert result["history_context"] == len(messages)
    assert len(mocked_ask.call_args_list[0].args[0]["chat"]["messages"]) == 10
    assert len(mocked_ask.call_args_list[1].args[0]["chat"]["messages"]) == len(messages)
    assert result["answers"]["she_needs"]["choice"] == "action"


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
