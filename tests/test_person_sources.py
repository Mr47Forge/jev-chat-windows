# -*- coding: utf-8 -*-
import importlib


def _memory(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    return importlib.reload(memory)


def test_person_can_exist_without_any_chat_platform(tmp_path, monkeypatch):
    memory = _memory(tmp_path, monkeypatch)
    memory.ensure_person("p1", "她", "恋爱对象")
    sid = memory.add_source_item(
        "p1",
        "我观察到她被夸工作能力时明显更愿意继续聊。",
        source_kind="observation",
        platform="offline",
    )
    memory.add_dialogue_entry("p1", "user", "这是一条观察", source_item_id=sid)

    person = memory.person_record("p1")
    assert person["display_name"] == "她"
    assert memory.source_items("p1")[0]["platform"] == "offline"
    assert memory.dialogue("p1")[0]["source_item_id"] == sid


def test_observation_cannot_be_promoted_to_explicit_fact():
    from core.persona import person_agent

    got = person_agent._normalize({
        "reply": "收到",
        "memories": [{
            "kind": "profile",
            "content": "喜欢被夸",
            "certainty": "explicit",
            "confidence": 1.0,
            "evidence": "用户自己的观察",
        }],
        "intimacy": [{
            "dimension": "主导/顺从",
            "value": "偏顺从",
            "scope": "fantasy",
            "certainty": "explicit",
            "confidence": 1.0,
            "evidence": "用户自己的观察",
        }],
    }, "observation")

    assert got["memories"][0]["certainty"] == "inferred"
    assert got["memories"][0]["confidence"] <= 0.75
    assert got["intimacy"][0]["certainty"] == "inferred"
    assert got["intimacy"][0]["confidence"] <= 0.55


def test_target_statement_can_remain_explicit():
    from core.persona import person_agent

    got = person_agent._normalize({
        "reply": "收到",
        "memories": [{
            "kind": "like",
            "content": "她明确说更喜欢别人夸做事能力",
            "certainty": "explicit",
            "confidence": 0.95,
            "evidence": "对方原话",
        }],
    }, "target_statement")
    assert got["memories"][0]["certainty"] == "explicit"


def test_intimacy_strategy_never_jumps_more_than_one_level():
    from core.persona import interaction_strategy

    got = interaction_strategy.normalize({
        "summary": "测试",
        "intimacy_progression": {
            "current_level": 2,
            "next_level": 8,
            "recommended_topics": ["测试"],
        },
    })
    assert got["intimacy_progression"]["current_level"] == 2
    assert got["intimacy_progression"]["next_level"] == 3


def test_markdown_export_contains_all_person_layers(tmp_path, monkeypatch):
    memory = _memory(tmp_path, monkeypatch)

    import app.chat_history as chat_history
    monkeypatch.setattr(chat_history, "_PATH", str(tmp_path / "chat_history.json"))

    memory.ensure_person("p2", "小A", "朋友")
    memory.remember(
        "p2", "communication", "更喜欢具体夸能力",
        certainty="inferred", confidence=0.7,
        source_id="m1", evidence="多次观察",
    )
    memory.add_relationship_snapshot(
        "p2", window_days=30, stage="熟悉期", trend="升温",
        summary="互动更主动", evidence="30天记录",
    )
    memory.add_intimacy_preference(
        "p2", "主动/被主动", "更喜欢对方主动一点",
        scope="topic_interest", certainty="inferred", confidence=0.5,
        source_id="i1", evidence="原始资料",
    )
    sid = memory.add_source_item(
        "p2", "她会认真回应能力方面的夸奖。",
        source_kind="observation", platform="douyin",
    )
    memory.add_dialogue_entry("p2", "user", "这是我的观察", source_item_id=sid)
    memory.add_dialogue_entry("p2", "assistant", "已记录。")
    memory.save_strategy_profile("p2", {
        "schema": "jev-interaction-strategy/v1",
        "summary": "优先具体夸能力",
        "praise": {"best_targets": []},
        "conversation": {},
        "emotional_support": {},
        "relationship_progression": {"current_stage": "熟悉期"},
        "intimacy_progression": {
            "current_level": 1, "current_name": "吸引与欣赏",
            "next_level": 2, "next_name": "轻暧昧",
        },
        "boundaries_and_risks": [],
        "unknowns": [],
    })

    from app.services import markdown_export_service
    text = markdown_export_service.build_person_markdown("p2")

    assert "人物长期记忆" in text
    assert "关系趋势" in text
    assert "亲密与性偏好画像" in text
    assert "互动攻略" in text
    assert "原始资料来源" in text
    assert "人物分析 Agent 对话" in text
    assert "douyin" in text
    assert "优先具体夸能力" in text


def test_context_can_use_non_wechat_person_memory(tmp_path, monkeypatch):
    memory = _memory(tmp_path, monkeypatch)
    memory.ensure_person("manual-person", "小B", "朋友")
    memory.remember(
        "manual-person",
        "communication",
        "不喜欢连续追问",
        certainty="inferred",
        confidence=0.7,
        source_id="obs1",
    )
    memory.save_strategy_profile("manual-person", {
        "schema": "jev-interaction-strategy/v1",
        "summary": "一次只问一个问题",
        "praise": {"best_targets": []},
        "conversation": {"works": []},
        "relationship_progression": {"current_stage": "熟悉期", "next_step": "保持轻松交流"},
        "intimacy_progression": {
            "current_level": 0, "current_name": "普通聊天",
            "next_level": 1, "next_name": "吸引与欣赏",
        },
        "boundaries_and_risks": [],
    })

    from app.services import context_service
    ctx = context_service.build("小B", [("her", "你好")])

    assert "不喜欢连续追问" in ctx["judge_relationship"]
    assert "一次只问一个问题" in ctx["relationship"]
    assert ctx["person_id"] == "manual-person"


def test_agent_chat_is_not_new_evidence():
    from core.persona import person_agent

    got = person_agent._normalize({
        "reply": "根据已有画像，我会这样理解。",
        "memories": [{
            "kind": "profile",
            "content": "模型乱提取的新结论",
            "certainty": "inferred",
            "confidence": 0.9,
        }],
        "intimacy": [{
            "dimension": "测试",
            "value": "测试",
            "scope": "fantasy",
            "certainty": "inferred",
            "confidence": 0.9,
        }],
    }, "agent_chat")
    assert got["memories"] == []
    assert got["intimacy"] == []
