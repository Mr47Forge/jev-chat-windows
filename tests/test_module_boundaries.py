# -*- coding: utf-8 -*-
import importlib


def _memory(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    return importlib.reload(memory)


def test_nonromantic_realtime_does_not_run_love_or_m3_questions():
    from core.questions import questions_for_relationship

    friend = questions_for_relationship("friends")
    romantic = questions_for_relationship("恋爱对象")
    legacy_romantic = questions_for_relationship("romantic partners")

    assert "relationship_stage" not in friend
    assert "m3_phase" not in friend
    assert "interaction_task" not in friend
    assert "flirt_lightly" not in friend["best_action"]["criteria"]
    assert "clarify_relationship" not in friend["best_action"]["criteria"]

    assert "relationship_stage" in romantic
    assert "m3_phase" in romantic
    assert "interaction_task" in romantic
    assert "flirt_lightly" in romantic["best_action"]["criteria"]
    assert "clarify_relationship" in romantic["best_action"]["criteria"]
    assert "m3_phase" in legacy_romantic


def test_love_questions_do_not_define_second_action_authority():
    from core.love_questions import LOVE_QUESTIONS, LOVE_GUIDE_FIELDS

    assert "love_action" not in LOVE_QUESTIONS
    assert all(name != "m3_phase" for name, _ in LOVE_GUIDE_FIELDS)


def test_module_policy_blocks_misusing_reference_projects():
    from core.persona.module_policy import module

    assert module("blaniel")["allow_real_person_behavior_predictor"] is False
    assert module("bigfive-llm-predictor")["allow_real_person_scoring"] is False
    assert module("kinkxknow")["allow_chat_inferred_scoring"] is False


def test_goutoujunshi_is_actually_wired_as_runtime_guidance():
    from core.goutou_guidance import context_for

    text = context_for("build_trust", "repair")
    assert "狗头军师上游依据" in text
    assert "vendor" not in text.lower()
    assert len(text) > 80


def test_profile_context_aggregates_exact_same_claim_and_excludes_strategy(tmp_path, monkeypatch):
    memory = _memory(tmp_path, monkeypatch)
    memory.ensure_person("p", "小A", "朋友")
    memory.remember(
        "p", "communication", "不喜欢连续追问",
        certainty="inferred", confidence=0.6,
        source_type="manual", source_id="a",
    )
    memory.remember(
        "p", "communication", "不喜欢连续追问",
        certainty="inferred", confidence=0.8,
        source_type="chat", source_id="b",
    )
    memory.remember(
        "p", "communication", "应该故意晚回",
        certainty="strategy", confidence=0.6,
        source_type="strategy", source_id="s",
    )

    text = memory.profile_context("p")
    assert "不喜欢连续追问" in text
    assert "证据×2" in text
    assert "应该故意晚回" not in text


def test_strategy_model_does_not_receive_raw_source_items(tmp_path, monkeypatch):
    memory = _memory(tmp_path, monkeypatch)
    memory.ensure_person("p2", "小B", "恋爱对象")
    memory.add_source_item(
        "p2",
        "这是一段未经结构化的原始观察，不能直接进策略提示。",
        source_kind="observation",
        platform="manual",
    )
    memory.remember(
        "p2", "communication", "更喜欢一次只聊一个问题",
        certainty="inferred", confidence=0.7, source_id="structured",
    )

    from app.services import strategy_service

    monkeypatch.setattr(strategy_service.settings, "has_llm_key", lambda: True)
    monkeypatch.setattr(strategy_service.settings, "draft_provider", lambda: "deepseek")
    monkeypatch.setattr(strategy_service.settings, "draft_model", lambda: "")
    monkeypatch.setattr(strategy_service.settings, "draft_base_url", lambda: "")
    monkeypatch.setattr(strategy_service.settings, "llm_key", lambda: "test")
    monkeypatch.setattr(strategy_service.settings, "thinking", lambda: False)

    captured = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return {
            "schema": "jev-interaction-strategy/v1",
            "summary": "测试",
            "praise": {"best_targets": [], "avoid": []},
            "conversation": {"works": [], "avoid": []},
            "emotional_support": {},
            "relationship_progression": {"current_stage": "测试"},
            "intimacy_progression": {},
            "boundaries_and_risks": [],
            "unknowns": [],
            "confidence": 0.5,
        }

    monkeypatch.setattr(strategy_service.interaction_strategy, "generate", fake_generate)
    strategy_service.generate_strategy_for_person("p2", include_intimacy=False)

    combined = str(captured)
    assert "更喜欢一次只聊一个问题" in combined
    assert "未经结构化的原始观察" not in combined
    assert "狗头军师长期策略依据" in captured["framework_context"]
    assert "狗头军师长期策略依据" not in captured["notes"]
    assert captured["include_intimacy"] is False


def test_draft_priority_keeps_persona_below_live_action():
    from core import draft

    assert "人格 Skill、M3/PUA术语、长期攻略不能改写本轮主要动作" in draft.SYSTEM
