# -*- coding: utf-8 -*-
"""永久关系记忆回归测试。"""
import importlib


def test_relationship_memory_survives_module_reload(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))

    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.ensure_person("wxid_test", "测试对象")
    memory.remember(
        "wxid_test", "like", "喜欢吃火锅",
        source_type="wechat", source_id="msg-1",
        evidence="她：我最喜欢吃火锅",
    )

    # 模拟应用关闭后重新加载模块：不能依赖进程内变量。
    memory = importlib.reload(memory)
    rows = memory.recall("wxid_test")
    assert len(rows) == 1
    assert rows[0]["content"] == "喜欢吃火锅"
    assert rows[0]["evidence"] == "她：我最喜欢吃火锅"
    assert "喜欢吃火锅" in memory.profile_context("wxid_test")


def test_relationship_memory_isolated_by_person(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))

    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.remember("a", "like", "喜欢A")
    memory.remember("b", "like", "喜欢B")

    assert [x["content"] for x in memory.recall("a")] == ["喜欢A"]
    assert [x["content"] for x in memory.recall("b")] == ["喜欢B"]


def test_inference_is_marked_and_cannot_become_full_confidence(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.remember("x", "profile", "可能比较在意仪式感",
                    certainty="inferred", confidence=1.0, source_id="guess-1")
    row = memory.recall("x")[0]
    assert row["certainty"] == "inferred"
    assert row["confidence"] <= 0.85
    assert "（推测）可能比较在意仪式感" in memory.profile_context("x")


def test_new_explicit_memory_can_supersede_old_one(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    old_id = memory.remember("x", "dislike", "不吃辣", certainty="explicit",
                             source_id="old", source_time=100)
    memory.remember("x", "like", "现在开始喜欢吃辣", certainty="explicit",
                    source_id="new", source_time=200, valid_from=200,
                    supersedes_id=old_id)
    active = memory.recall("x")
    assert [x["content"] for x in active] == ["现在开始喜欢吃辣"]


def test_relationship_profile_and_trend_are_separate(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.remember("x", "like", "喜欢火锅", source_id="m1")
    memory.add_relationship_snapshot(
        "x", window_days=30, stage="暧昧", trend="升温",
        summary="最近主动联系增加", observed_at=1000,
    )
    ctx = memory.memory_context("x")
    assert "【喜欢】" in ctx
    assert "喜欢火锅" in ctx
    assert "【我们的关系趋势】" in ctx
    assert "趋势=升温" in ctx


def test_learning_can_be_paused_without_deleting_memory(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.remember("x", "promise", "周末一起吃饭", source_id="p1")
    memory.set_learning("x", False)
    assert memory.learning_enabled("x") is False
    assert memory.recall("x")[0]["content"] == "周末一起吃饭"
