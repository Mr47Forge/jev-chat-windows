"""
wechat_platform/base.py — Platform abstraction for WeChat data discovery.

Cross-platform code (export_contact.py, main.py) depends only on this
abstract base. Concrete implementation lives in windows.py.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class WeChatPlatform(ABC):
    """Abstract base for platform-specific WeChat data discovery."""

    NAME: str = "unknown"

    @abstractmethod
    def default_decrypted_db_dir(self) -> Optional[Path]:
        """Default location to search for the decrypted db_storage directory.

        Returned path may be either:
          - a db_storage directory directly (containing contact/, message/, ...)
          - a parent directory containing wxid_*/db_storage subdirs
        Returns None if no default is known on this platform.
        """

    @abstractmethod
    def find_self_wxid_from_fs(self) -> Optional[str]:
        """Look up own wxid from WeChat's local data directory.

        Returns None if not found or ambiguous; the caller will fall back
        to detecting it from the Name2Id table in the decrypted DB.
        """

    @abstractmethod
    def find_avatar_in_fs(self, wxid: str) -> Optional[str]:
        """Search the filesystem cache for an avatar image of the given wxid.

        Returns an absolute file path to a valid image, or None. The caller
        will fall back to extracting from head_image.db if available.
        """

    @abstractmethod
    def open_file(self, path: Path) -> bool:
        """Open a file with the system default application. Returns True on success."""

    @abstractmethod
    def open_command(self) -> str:
        """The shell command name a user can type to open a file (e.g. 'open', 'start').
        Used only for printing user-facing instructions."""
