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
