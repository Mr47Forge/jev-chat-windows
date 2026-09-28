# -*- coding: utf-8 -*-
"""TraceMemo 本地 API 适配层。

不复制 TraceMemo 的内部实现；只通过其本机 HTTP API读取用户主动选择的联系人。
这样 Jev 不需要 OCR 历史聊天，也不会默认遍历整个微信。

TraceMemo: https://github.com/Wxw-Gu/TraceMemo
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class WeChatHistoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SelectedContact:
    id: str
    name: str


class TraceMemoProvider:
    def __init__(self, base_url: str = "http://127.0.0.1:6131", token: str = "", timeout: float = 20):
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None):
        url = self.base_url + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None and v != ""}
            if clean:
                url += "?" + urlencode(clean)
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        try:
            with urlopen(Request(url, headers=headers), timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise WeChatHistoryError(f"微信历史接口 HTTP {exc.code}") from exc
        except URLError as exc:
            raise WeChatHistoryError(f"无法连接微信历史接口：{exc.reason}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise WeChatHistoryError("微信历史接口返回的不是有效 JSON") from exc

    def health(self):
        """只检查本地服务，不读取任何聊天。"""
        for path in ("/api/v1/health", "/api/v1/status"):
            try:
                return self._get(path)
            except WeChatHistoryError:
                continue
        raise WeChatHistoryError("TraceMemo 本地 API 未就绪")

    def contacts(self):
        """列出联系人供用户手动选择；本方法不导入聊天内容。"""
        candidates = (
            "/api/v1/contacts",
            "/api/v1/wechat/contacts",
            "/api/v1/query/contacts",
        )
        last = None
        for path in candidates:
            try:
                data = self._get(path)
                if data is not None:
                    return data
            except WeChatHistoryError as exc:
                last = exc
        raise last or WeChatHistoryError("当前 TraceMemo 版本没有可用的联系人接口")

    def messages_for_contact(
        self,
        contact_id: str,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int | None = None,
    ):
        """读取一个明确 contact_id 的聊天。

        故意不提供“全部联系人”入口，避免误把整个微信导入 Jev。
        """
        if not str(contact_id).strip():
            raise ValueError("必须先明确选择一个微信联系人")
        params = {
            "contactId": contact_id,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit,
        }
        candidates = (
            "/api/v1/chatlog",
            "/api/v1/query/messages",
            "/api/v1/messages",
        )
        last = None
        for path in candidates:
            try:
                data = self._get(path, params)
                if data is not None:
                    return data
            except WeChatHistoryError as exc:
                last = exc
        raise last or WeChatHistoryError("当前 TraceMemo 版本没有可用的消息接口")

    def media(self, media_id: str) -> bytes:
        """取得数据库消息对应的原始媒体；不使用屏幕截图/OCR。"""
        if not str(media_id).strip():
            raise ValueError("media_id 不能为空")
        url = self.base_url + "/api/v1/media/" + str(media_id)
        headers = {}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        try:
            with urlopen(Request(url, headers=headers), timeout=self.timeout) as response:
                return response.read()
        except (HTTPError, URLError) as exc:
            raise WeChatHistoryError("读取微信原始媒体失败") from exc
