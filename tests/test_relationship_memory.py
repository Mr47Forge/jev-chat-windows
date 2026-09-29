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
    profile = memory.profile_context("x")
    assert "可能比较在意仪式感" in profile
    assert "推测 85%" in profile
    assert "证据×1" in profile


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


def test_intimacy_preference_separates_fantasy_from_real_world(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.add_intimacy_preference(
        "x", "权力交换", "偏好被主导",
        scope="fantasy", certainty="inferred", confidence=0.95,
        source_type="wechat", source_id="m1", evidence="多次主动讨论相关幻想",
    )
    row = memory.recall_intimacy_preferences("x")[0]
    assert row["scope"] == "fantasy"
    assert row["certainty"] == "inferred"
    assert row["confidence"] <= 0.75

    # 普通聊天上下文默认绝不注入敏感画像。
    assert "权力交换" not in memory.memory_context("x")
    sensitive = memory.memory_context("x", include_intimacy=True)
    assert "【幻想偏好】" in sensitive
    assert "偏好被主导" in sensitive
    assert "不等于现实意愿" in sensitive


def test_inferred_real_world_intimacy_is_strictly_capped(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.add_intimacy_preference(
        "x", "公开情境刺激", "可能愿意现实尝试",
        scope="real_world_willingness", certainty="inferred", confidence=1.0,
        source_id="m2",
    )
    row = memory.recall_intimacy_preferences("x")[0]
    assert row["confidence"] <= 0.60


def test_intimacy_boundary_and_experience_are_distinct(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.add_intimacy_preference(
        "x", "疼痛刺激", "明确拒绝",
        scope="boundary", certainty="explicit", source_id="b1",
    )
    memory.add_intimacy_preference(
        "x", "角色扮演", "曾明确说尝试过",
        scope="experience", certainty="explicit", source_id="e1",
    )
    scopes = {x["scope"] for x in memory.recall_intimacy_preferences("x")}
    assert scopes == {"boundary", "experience"}


def test_ensure_person_does_not_overwrite_relationship_on_memory_write(tmp_path, monkeypatch):
    monkeypatch.setenv("JEV_DATA_DIR", str(tmp_path))
    import app.relationship_memory as memory
    memory = importlib.reload(memory)

    memory.ensure_person("x", "对象", "朋友")
    memory.remember("x", "like", "咖啡", source_id="m1")
    with memory._db() as con:
        row = con.execute("SELECT relationship FROM people WHERE person_id='x'").fetchone()
    assert row["relationship"] == "朋友"
