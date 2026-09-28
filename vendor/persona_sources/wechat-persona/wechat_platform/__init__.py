"""
wechat_platform — Windows platform helpers for WeChat data access.

Usage:
    from wechat_platform import current
    plat = current()
    wxid = plat.find_self_wxid_from_fs()
"""

import sys
from functools import lru_cache

from .base import WeChatPlatform


@lru_cache(maxsize=1)
def current() -> WeChatPlatform:
    """Return the platform implementation (Windows only)."""
    if sys.platform == "win32":
        from .windows import WindowsPlatform
        return WindowsPlatform()
    raise RuntimeError(
        f"unsupported platform: {sys.platform}. "
        "This fork only supports Windows (win32). "
        "For macOS, see the original project: https://github.com/Jiang59991/ginger_wechat_portrait"
    )


__all__ = ["WeChatPlatform", "current"]
