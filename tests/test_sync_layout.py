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


def test_full_vendor_sync_committed_files_ignored_by_upstream_gitignore():
    # PersonaMem-v3 的这些文件会被它自己的 .gitignore 命中；
    # vendor-sync 必须用 git add -f，否则“整仓同步”会悄悄漏文件。
    assert (ROOT / "vendor/persona_sources/personamem-v3/data/gistbench_sample_10users.csv").exists()
    assert (ROOT / "vendor/persona_sources/personamem-v3/results/_scripts/accuracy_agreement.py").exists()


def test_every_upstream_snapshot_has_lock_and_local_metadata():
    cfg = json.loads((ROOT / "vendor/upstreams.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "vendor/UPSTREAMS.lock.json").read_text(encoding="utf-8"))
    locked = lock["sources"]
    for item in cfg["sources"]:
        target = ROOT / item["target"]
        assert target.is_dir(), item["name"]
        meta_path = target / "_JEV_UPSTREAM.json"
        assert meta_path.exists(), item["name"]
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["commit"] == locked[item["name"]]["commit"]
