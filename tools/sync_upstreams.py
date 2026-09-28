# -*- coding: utf-8 -*-
"""完整同步 Jev 使用的外部项目。

原则：
- 不再手工挑文件；每个上游仓库按指定 ref 整仓复制（仅去掉其 .git 元数据）。
- adapters / Jev 自己的代码放在 app/ 和 core/，不写进 vendor 源仓库目录。
- 每次同步写 vendor/UPSTREAMS.lock.json，记录实际 commit。
- --check 只比较远端 SHA 与 lock，不改文件。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "vendor" / "upstreams.json"
LOCK = ROOT / "vendor" / "UPSTREAMS.lock.json"


def _run(args: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode:
        raise RuntimeError(
            "命令失败：" + " ".join(args) + "\n" +
            (proc.stderr or proc.stdout).strip()[-2000:]
        )
    return proc.stdout.strip()


def _load_config() -> dict:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if data.get("schema") != "jev-upstreams/v1":
        raise RuntimeError("vendor/upstreams.json schema 不受支持")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("vendor/upstreams.json 没有 sources")
    return data


def _load_lock() -> dict:
    try:
        data = json.loads(LOCK.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _safe_target(rel: str) -> Path:
    target = (ROOT / rel).resolve()
    vendor = (ROOT / "vendor").resolve()
    if target == vendor or vendor not in target.parents:
        raise RuntimeError("上游 target 必须位于 vendor/ 下：" + rel)
    return target


def _remote_sha(repo: str, ref: str) -> str:
    url = "https://github.com/" + repo + ".git"
    lines = _run(["git", "ls-remote", url, ref]).splitlines()
    if not lines:
        raise RuntimeError("找不到远端 ref：" + repo + " " + ref)
    return lines[0].split()[0]


def _clone_full(repo: str, ref: str, destination: Path) -> str:
    url = "https://github.com/" + repo + ".git"
    _run([
        "git", "clone",
        "--depth", "1",
        "--branch", ref,
        "--recurse-submodules",
        url,
        str(destination),
    ])
    return _run(["git", "rev-parse", "HEAD"], cwd=destination)


def _copy_complete(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    def ignore(path: str, names: list[str]) -> set[str]:
        return {".git"} if ".git" in names else set()

    shutil.copytree(source, target, ignore=ignore)


def sync(names: set[str] | None = None) -> dict:
    cfg = _load_config()
    previous = _load_lock().get("sources") or {}
    locked: dict[str, dict] = {}
    now = datetime.now(timezone.utc).isoformat()

    configured = {str(item.get("name")) for item in cfg["sources"]}
    if names:
        missing = sorted(names - configured)
        if missing:
            raise RuntimeError("未知上游：" + ", ".join(missing))

    with tempfile.TemporaryDirectory(prefix="jev-upstream-sync-") as td:
        temp = Path(td)
        for item in cfg["sources"]:
            name = str(item["name"])
            if names and name not in names:
                old = previous.get(name)
                if old:
                    locked[name] = old
                continue

            repo = str(item["repo"])
            ref = str(item["ref"])
            target_rel = str(item["target"])
            target = _safe_target(target_rel)

            print("[同步]", name, repo, ref)
            clone = temp / name
            sha = _clone_full(repo, ref, clone)
            _copy_complete(clone, target)

            meta = {
                "name": name,
                "repo": repo,
                "ref": ref,
                "commit": sha,
                "target": target_rel.replace("\\", "/"),
                "synced_at": now,
            }
            (target / "_JEV_UPSTREAM.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            locked[name] = meta

    for name, old in previous.items():
        locked.setdefault(name, old)

    LOCK.write_text(
        json.dumps(
            {
                "schema": "jev-upstreams-lock/v1",
                "updated_at": now,
                "sources": dict(sorted(locked.items())),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return locked


def check(names: set[str] | None = None) -> int:
    cfg = _load_config()
    lock = _load_lock().get("sources") or {}
    stale = 0

    for item in cfg["sources"]:
        name = str(item["name"])
        if names and name not in names:
            continue
        repo = str(item["repo"])
        ref = str(item["ref"])
        remote = _remote_sha(repo, ref)
        local = str((lock.get(name) or {}).get("commit") or "")
        if remote == local:
            print("[最新]", name, remote[:12])
        else:
            stale += 1
            print("[有更新]", name, "本地", local[:12] or "无", "远端", remote[:12])

    return 1 if stale else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Jev 外部项目完整同步器")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--sync", nargs="+", metavar="NAME", help="同步指定源；all 表示全部")
    action.add_argument("--check", nargs="*", metavar="NAME", help="只检查是否有上游更新")
    args = parser.parse_args()

    if args.sync is not None:
        names = None if "all" in args.sync else set(args.sync)
        sync(names)
        return 0

    names = set(args.check or []) or None
    return check(names)


if __name__ == "__main__":
    raise SystemExit(main())
