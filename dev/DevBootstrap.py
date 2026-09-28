# -*- coding: utf-8 -*-
"""JevChat 开发版启动器。

PyInstaller 只冻结 Python 运行时和第三方依赖；真正业务代码 main.py / app / core / vendor
全部留在 exe 外面。普通业务修改由 V2 同步器按 dev/runtime-sync.txt 替换，
不需要重打整个运行时。
"""
from __future__ import annotations

import ctypes
import os
import runpy
import sys
import traceback


def _root() -> str:
    return os.path.dirname(sys.executable)


def _message(text: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, text, "JevChat 开发版", 0x10)
    except Exception:
        pass


def main() -> None:
    root = _root()
    entry = os.path.join(root, "main.py")
    if not os.path.isfile(entry):
        _message("缺少 main.py。请运行“更新开发源码.exe”，或重新下载开发环境。")
        return

    required = (
        os.path.join(root, "app"),
        os.path.join(root, "core"),
        os.path.join(root, "vendor"),
        os.path.join(root, "runtime-generation.txt"),
    )
    missing = [os.path.basename(x) for x in required if not os.path.exists(x)]
    if missing:
        _message(
            "开发环境结构不完整：缺少 " + "、".join(missing) +
            "\n\n当前项目已经升级到 V2 结构，请重新下载最新 JevChat-Windows-Dev。"
        )
        return

    os.chdir(root)
    if root not in sys.path:
        sys.path.insert(0, root)

    try:
        runpy.run_path(entry, run_name="__main__")
    except SystemExit:
        raise
    except Exception:
        detail = traceback.format_exc()
        _message("启动失败。\n\n" + detail[-3000:])


if __name__ == "__main__":
    main()
