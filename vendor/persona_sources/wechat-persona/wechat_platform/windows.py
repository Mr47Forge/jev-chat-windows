"""
wechat_platform/windows.py — Windows implementation.

Layout assumptions for WeChat for Windows 4.x:
  * Data directory (default):  %USERPROFILE%\\Documents\\xwechat_files\\<wxid>\\db_storage\\
    Overridable via config.json `xwechat_files_dir` or env WECHAT_XWECHAT_FILES_DIR.
  * Process name:               Weixin.exe  (NOT WeChat.exe — that's legacy 3.x)
  * Encryption:                 SQLCipher 4 (HMAC-SHA512, 256000 PBKDF2 iterations)

Decryption is NOT included in this project. Users must decrypt their
databases externally (e.g. using ylytdeng/wechat-decrypt) and point
config.json `decrypted_db_dir` to the output. This module only reads
from already-decrypted databases.

Avatar caching layout in WeChat Win 4.x is not yet documented; we try a
few candidate sub-paths and otherwise fall back to head_image.db (handled
in the cross-platform layer of export_contact.py).
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .base import WeChatPlatform


_IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"RIFF", b"\x00\x00\x01\x00")

# Default layout; overridable via config.json key `xwechat_files_dir` or
# environment variable WECHAT_XWECHAT_FILES_DIR, because many users change
# WeChat's file-storage location in Settings → File Management and the
# data ends up on a different drive (e.g. D:\WeChat\xwechat_files).
_DEFAULT_DATA_DIR = Path.home() / "Documents" / "xwechat_files"
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def _resolve_data_dir() -> Path:
    env_val = os.environ.get("WECHAT_XWECHAT_FILES_DIR")
    if env_val:
        return Path(env_val).expanduser()
    if _CONFIG_PATH.exists():
        try:
            cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            custom = cfg.get("xwechat_files_dir")
            if custom:
                return Path(custom).expanduser()
        except Exception:
            pass
    return _DEFAULT_DATA_DIR


class WindowsPlatform(WeChatPlatform):
    NAME = "windows"

    def default_decrypted_db_dir(self) -> Optional[Path]:
        candidate = Path.home() / "Documents" / "wechat_decrypted"
        return candidate if candidate.exists() else None

    def find_self_wxid_from_fs(self) -> Optional[str]:
        """Detect own wxid.

        Priority:
          1. config.json `last_decrypted_wxid` (written by the decrypt tool)
             — this is the directory name the user chose to decrypt, so it's
             authoritative when multiple accounts are present.
          2. If there is exactly one wxid directory, use it.
          3. None — caller falls back to the Name2Id heuristic.

        The returned wxid has the directory suffix (`_<4hex>`) stripped,
        because that suffix is a device-instance hash, not part of the
        account's actual wxid (the wxid stored in contact/message DBs).
        """
        if _CONFIG_PATH.exists():
            try:
                cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                last = cfg.get("last_decrypted_wxid")
                if last:
                    return self._strip_dir_suffix(last)
            except Exception:
                pass
        wxids = self.list_wxids()
        if len(wxids) == 1:
            return self._strip_dir_suffix(wxids[0])
        return None

    @staticmethod
    def _strip_dir_suffix(dir_name: str) -> str:
        """Turn a wxid directory name into the real wxid.

        WeChat for Windows 4.x uses `wxid_<main>_<4hex>` as the per-install
        data directory name, where `_<4hex>` identifies the local instance.
        The DB-level wxid is just `wxid_<main>`. Example:
            wxid_abc1234defgh56_fa7d  →  wxid_abc1234defgh56
        If the name doesn't match the expected pattern, return it unchanged.
        """
        # Require at least 10 chars in the main part; real WeChat wxids
        # have ~14-16 random chars, so 10 is a safe lower bound that
        # prevents stripping when a wxid happens to end in _[a-f0-9]{4}.
        m = re.match(r"^(wxid_[a-z0-9]{10,})_[a-f0-9]{4}$", dir_name)
        return m.group(1) if m else dir_name

    def list_wxids(self) -> List[str]:
        """Return directory names (with suffix) under xwechat_files."""
        if not _resolve_data_dir().exists():
            return []
        return sorted(
            d.name for d in _resolve_data_dir().iterdir()
            if d.is_dir() and d.name.startswith("wxid_")
        )

    def find_avatar_in_fs(self, wxid: str) -> Optional[str]:
        if not _resolve_data_dir().exists():
            return None
        wxid_md5 = hashlib.md5(wxid.encode()).hexdigest()
        sub_dirs = ("msg/avatar", "avatar", "Avatars", "msg/avatars")
        for user_dir in _resolve_data_dir().iterdir():
            if not user_dir.is_dir():
                continue
            for sub in sub_dirs:
                base = user_dir / sub
                if not base.exists():
                    continue
                for cand in [base / wxid_md5, *base.glob(f"{wxid_md5}*")]:
                    if not cand.is_file():
                        continue
                    try:
                        with open(cand, "rb") as f:
                            header = f.read(8)
                        if any(header.startswith(sig) for sig in _IMAGE_MAGIC):
                            return str(cand)
                    except Exception:
                        continue
        return None

    def open_file(self, path: Path) -> bool:
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
        except Exception:
            return False

    def open_command(self) -> str:
        return "start"

    # ── Windows-only helpers ─────────────────────────────────────────────────

    def wechat_decrypt_dir(self) -> Path:
        """Expected install location of the ylytdeng/wechat-decrypt clone."""
        return Path.home() / "Documents" / "wechat-decrypt"

    def is_wechat_decrypt_installed(self) -> bool:
        """True if the wechat-decrypt clone exists and looks usable."""
        d = self.wechat_decrypt_dir()
        return d.exists() and (d / "main.py").exists()

    def is_weixin_running(self) -> Optional[bool]:
        """True/False if Weixin.exe is in the task list, None if check failed."""
        if sys.platform != "win32":
            return None
        try:
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Weixin.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
            )
            return "Weixin.exe" in out.stdout
        except Exception:
            return None
