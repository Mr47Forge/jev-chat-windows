# -*- coding: utf-8 -*-
"""恋爱对象白名单。

只有用户主动选中的微信联系人才能进入关系记忆处理链。
"""
from __future__ import annotations

import json
from pathlib import Path


class RelationshipSelection:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict:
        if not self.path.exists():
            return {"contacts": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"contacts": []}
        contacts = data.get("contacts")
        return {"contacts": contacts if isinstance(contacts, list) else []}

    def ids(self) -> set[str]:
        return {str(x.get("id")) for x in self.load()["contacts"] if isinstance(x, dict) and x.get("id")}

    def select(self, contact_id: str, name: str = "", relationship: str = "恋爱对象") -> None:
        contact_id = str(contact_id).strip()
        if not contact_id:
            raise ValueError("contact_id 不能为空")
        data = self.load()
        contacts = [x for x in data["contacts"] if str(x.get("id")) != contact_id]
        contacts.append({"id": contact_id, "name": str(name), "relationship": str(relationship)})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"contacts": contacts}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def remove(self, contact_id: str) -> None:
        data = self.load()
        contacts = [x for x in data["contacts"] if str(x.get("id")) != str(contact_id)]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"contacts": contacts}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
