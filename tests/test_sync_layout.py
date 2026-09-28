# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _parse_runtime_manifest():
    data = {"dir": [], "file": [], "required": [], "generation": []}
    for raw in (ROOT / "dev" / "runtime-sync.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "JEV_RUNTIME_SYNC_V2":
            continue
        key, value = line.split("=", 1)
        data.setdefault(key, []).append(value.strip())
    return data


def test_runtime_sync_manifest_matches_current_project_structure():
    plan = _parse_runtime_manifest()
    assert plan["generation"] == ["2"]
    assert {"app", "core", "vendor"} <= set(plan["dir"])
    assert "main.py" in plan["file"]

    for rel in plan["required"]:
        assert (ROOT / rel).exists(), rel


def test_runtime_sync_manifest_never_overwrites_user_data():
    plan = _parse_runtime_manifest()
    targets = set(plan["dir"] + plan["file"])
    forbidden = {
        "config.json",
        "chat_profiles.json",
        "knowledge.json",
        "persona_skills.json",
        "chat_history.json",
        "relationship_memory.db",
        "_internal",
    }
    assert targets.isdisjoint(forbidden)


def test_upstream_targets_are_unique_and_live_under_vendor():
    data = json.loads((ROOT / "vendor" / "upstreams.json").read_text(encoding="utf-8"))
    assert data["schema"] == "jev-upstreams/v1"
    targets = [x["target"] for x in data["sources"]]
    names = [x["name"] for x in data["sources"]]
    assert len(targets) == len(set(targets))
    assert len(names) == len(set(names))
    assert all(x.startswith("vendor/") for x in targets)


def test_upstream_set_includes_persona_and_intimacy_sources():
    data = json.loads((ROOT / "vendor" / "upstreams.json").read_text(encoding="utf-8"))
    names = {x["name"] for x in data["sources"]}
    assert {
        "goutoujunshi",
        "wechat-persona",
        "o-mem",
        "personamem-v3",
        "blaniel",
        "bigfive-llm-predictor",
        "kinkdirectory",
        "relationship-atlas",
        "kinkxknow",
        "klist",
    } <= names
