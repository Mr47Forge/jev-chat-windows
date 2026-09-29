# -*- coding: utf-8 -*-
"""平台无关的人物分析工作台。

用途：
- 没有聊天记录：直接输入自己的观察；
- 有对方原话：作为“对方明确说过”输入；
- 抖音/QQ/Telegram/其它平台：直接粘贴聊天或平台导出；
- 和人物分析 Agent 连续对话；
- 生成/刷新互动攻略；
- 导出当前人物或全部人物为 Markdown。
"""
from __future__ import annotations

import re
import threading

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from app import relationship_memory
from app.services import markdown_export_service, person_input_service, strategy_service
from core.persona.module_policy import is_romantic_relationship


_SOURCE_TYPES = [
    ("我的观察", "observation"),
    ("只和 Agent 讨论（不作为证据）", "agent_chat"),
    ("对方明确说过", "target_statement"),
    ("粘贴聊天", "chat_paste"),
    ("平台导入/记录", "platform_import"),
    ("其他补充", "note"),
]

_PLATFORMS = [
    ("手工输入", "manual"),
    ("线下观察", "offline"),
    ("微信", "wechat"),
    ("抖音", "douyin"),
    ("QQ", "qq"),
    ("Telegram", "telegram"),
    ("小红书", "xiaohongshu"),
    ("微博", "weibo"),
    ("其他", "other"),
]


class PersonWorkspace(QDialog):
    analysisDone = Signal(bool, object, str)
    strategyDone = Signal(bool, object, str)

    def __init__(self, parent=None, initial_person: str = ""):
        super().__init__(parent)
        self.setWindowTitle("人物分析")
        self.resize(760, 780)
        self.setModal(False)
        self._people = []
        self._busy = False

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("人物"))
        self.personBox = QComboBox()
        self.personBox.setMinimumWidth(240)
        self.personBox.currentIndexChanged.connect(self._person_changed)
        top.addWidget(self.personBox, 1)
        self.newName = QLineEdit()
        self.newName.setPlaceholderText("新建人物名称")
        top.addWidget(self.newName, 1)
        self.newRelationship = QComboBox()
        self.newRelationship.setEditable(True)
        self.newRelationship.addItems(["未设置", "恋爱对象", "暧昧对象", "伴侣", "朋友", "同事", "家人", "其他"])
        self.newRelationship.setMaximumWidth(120)
        top.addWidget(self.newRelationship)
        self.newButton = QPushButton("新建")
        self.newButton.clicked.connect(self._create_person)
        top.addWidget(self.newButton)
        root.addLayout(top)

        meta = QFormLayout()
        self.sourceBox = QComboBox()
        for label, value in _SOURCE_TYPES:
            self.sourceBox.addItem(label, value)
        meta.addRow("本次资料类型", self.sourceBox)

        self.platformBox = QComboBox()
        self.platformBox.setEditable(True)
        for label, value in _PLATFORMS:
            self.platformBox.addItem(label, value)
        meta.addRow("来源平台", self.platformBox)
        self.intimacyCheck = QCheckBox("本次允许分析亲密/性偏好")
        self.intimacyCheck.setToolTip("默认只对明确恋爱/暧昧/伴侣关系开启；也可以手动覆盖本次输入。")
        meta.addRow("敏感画像", self.intimacyCheck)
        root.addLayout(meta)

        self.inputEdit = QPlainTextEdit()
        self.inputEdit.setPlaceholderText(
            "直接告诉 Agent 你观察到什么，或者粘贴其它平台聊天。\n\n"
            "例如：\n"
            "她平时别人夸她工作能力时明显更开心，但别人只夸外貌她一般只回谢谢。\n\n"
            "也可以粘贴：\n"
            "我：你今天挺厉害的\n"
            "她：我更喜欢别人夸我做事，不太习惯一直夸长相"
        )
        self.inputEdit.setMinimumHeight(150)
        root.addWidget(self.inputEdit)

        action = QHBoxLayout()
        self.sendButton = QPushButton("发送给人物分析 Agent")
        self.sendButton.clicked.connect(self._submit)
        action.addWidget(self.sendButton)
        self.strategyButton = QPushButton("生成 / 刷新攻略")
        self.strategyButton.clicked.connect(self._generate_strategy)
        action.addWidget(self.strategyButton)
        action.addStretch(1)
        self.exportButton = QPushButton("导出当前 MD")
        self.exportButton.clicked.connect(self._export_current)
        action.addWidget(self.exportButton)
        self.exportAllButton = QPushButton("导出全部 MD")
        self.exportAllButton.clicked.connect(self._export_all)
        action.addWidget(self.exportAllButton)
        root.addLayout(action)

        self.statusLabel = QLabel("")
        root.addWidget(self.statusLabel)

        tabs = QTabWidget()
        self.dialogueEdit = QPlainTextEdit()
        self.dialogueEdit.setReadOnly(True)
        tabs.addTab(self.dialogueEdit, "和 Agent 的人物分析对话")

        self.strategyEdit = QPlainTextEdit()
        self.strategyEdit.setReadOnly(True)
        tabs.addTab(self.strategyEdit, "当前互动攻略")

        self.sourceEdit = QPlainTextEdit()
        self.sourceEdit.setReadOnly(True)
        tabs.addTab(self.sourceEdit, "已喂入的原始资料")
        root.addWidget(tabs, 1)

        self.analysisDone.connect(self._analysis_finished)
        self.strategyDone.connect(self._strategy_finished)

        self._refresh_people(initial_person)

    def _current_person_id(self) -> str:
        idx = self.personBox.currentIndex()
        if 0 <= idx < len(self._people):
            return str(self._people[idx]["person_id"])
        return ""

    def _current_person(self) -> dict:
        idx = self.personBox.currentIndex()
        return self._people[idx] if 0 <= idx < len(self._people) else {}

    def _refresh_people(self, select: str = ""):
        # 当前聊天标题可能是群名，不能因为打开工作台就偷偷创建“人物”。
        # 找得到已有人物才自动选中；找不到只把名字预填到“新建人物”输入框。
        resolved = relationship_memory.resolve_person_id(select) if select else ""
        if select and not relationship_memory.person_record(resolved):
            self.newName.setText(select)

        people = person_input_service.people()
        self._people = people
        self.personBox.blockSignals(True)
        self.personBox.clear()
        for p in people:
            label = p.get("display_name") or p.get("person_id")
            self.personBox.addItem(str(label))
        self.personBox.blockSignals(False)

        if not people:
            self._clear_views()
            return

        target = resolved if resolved and relationship_memory.person_record(resolved) else str(people[0]["person_id"])
        index = next(
            (i for i, p in enumerate(people) if str(p.get("person_id")) == target),
            0,
        )
        self.personBox.setCurrentIndex(index)
        self._load_person()

    def _create_person(self):
        name = self.newName.text().strip()
        if not name:
            QMessageBox.warning(self, "人物分析", "先填写人物名称。")
            return
        try:
            person = person_input_service.create_person(
                name,
                relationship=self.newRelationship.currentText().strip() or "未设置",
            )
        except Exception as exc:
            QMessageBox.critical(self, "新建失败", str(exc))
            return
        self.newName.clear()
        self._refresh_people(str(person["person_id"]))

    def _person_changed(self, _index):
        self._load_person()

    def _clear_views(self):
        self.dialogueEdit.setPlainText("还没有人物。可以在上方直接新建一个，不需要先有微信聊天。")
        self.strategyEdit.setPlainText("暂无攻略。")
        self.sourceEdit.setPlainText("暂无资料。")
        self.sendButton.setEnabled(False)
        self.strategyButton.setEnabled(False)
        self.exportButton.setEnabled(False)

    def _load_person(self):
        pid = self._current_person_id()
        enabled = bool(pid)
        self.sendButton.setEnabled(enabled and not self._busy)
        self.strategyButton.setEnabled(enabled and not self._busy)
        self.exportButton.setEnabled(enabled)
        if not pid:
            self._clear_views()
            return

        relationship = str(self._current_person().get("relationship") or "")
        self.intimacyCheck.setChecked(is_romantic_relationship(relationship))

        dialogue = person_input_service.dialogue(pid, limit=300)
        if dialogue:
            lines = []
            for row in dialogue:
                who = "我" if row["role"] == "user" else "Agent"
                lines.append(f"{who}：{row['content']}")
            self.dialogueEdit.setPlainText("\n\n".join(lines))
        else:
            self.dialogueEdit.setPlainText(
                "还没有人物分析对话。\n\n"
                "你可以直接输入自己的观察，不要求先有聊天记录。"
            )

        strategy = relationship_memory.load_strategy_profile(pid)
        self.strategyEdit.setPlainText(self._strategy_text(strategy))

        sources = relationship_memory.source_items(pid, limit=500)
        if not sources:
            self.sourceEdit.setPlainText("暂无原始资料。")
        else:
            blocks = []
            for row in sources:
                blocks.append(
                    f"#{row['id']} · {row.get('platform')} · {row.get('source_kind')}\n"
                    f"{row.get('content')}"
                )
            self.sourceEdit.setPlainText("\n\n---\n\n".join(blocks))

    @staticmethod
    def _strategy_text(strategy: dict) -> str:
        if not strategy:
            return "暂无互动攻略。先喂入一些资料，再点“生成 / 刷新攻略”。"
        lines = []
        if strategy.get("summary"):
            lines += ["总体", str(strategy["summary"]), ""]

        praise = (strategy.get("praise") or {}).get("best_targets") or []
        lines.append("怎么夸")
        if not praise:
            lines.append("暂无")
        for x in praise:
            if not isinstance(x, dict):
                continue
            lines.append(
                f"- {x.get('target','')}\n"
                f"  为什么：{x.get('why','')}\n"
                f"  怎么夸：{x.get('how','')}\n"
                f"  示例：{x.get('example','')}"
            )

        progress = strategy.get("relationship_progression") or {}
        lines += [
            "",
            "关系推进",
            f"- 当前：{progress.get('current_stage','未知')}",
            f"- 下一步：{progress.get('next_step','暂无')}",
        ]
        for x in progress.get("examples") or []:
            lines.append("- 示例：" + str(x))

        intimacy = strategy.get("intimacy_progression") or {}
        lines += [
            "",
            "亲密话题深度（不是关系阶段）",
            f"- 当前：{intimacy.get('current_level',0)}级 {intimacy.get('current_name','')}",
            f"- 最多下一步：{intimacy.get('next_level',0)}级 {intimacy.get('next_name','')}",
        ]
        for x in intimacy.get("recommended_topics") or []:
            lines.append("- 当前可聊：" + str(x))
        for x in intimacy.get("transition_examples") or []:
            lines.append("- 过渡：" + str(x))
        for x in intimacy.get("do_not_jump_to") or []:
            lines.append("- 暂不要跳到：" + str(x))

        unknowns = strategy.get("unknowns") or []
        if unknowns:
            lines += ["", "还不知道"]
            lines.extend("- " + str(x) for x in unknowns)
        return "\n".join(lines)

    def _source_kind(self) -> str:
        return str(self.sourceBox.currentData() or "observation")

    def _platform(self) -> str:
        data = self.platformBox.currentData()
        text = self.platformBox.currentText().strip()
        if data and text in [x[0] for x in _PLATFORMS]:
            return str(data)
        return text or "other"

    def _set_busy(self, busy: bool, text: str = ""):
        self._busy = busy
        self.sendButton.setEnabled(not busy and bool(self._current_person_id()))
        self.strategyButton.setEnabled(not busy and bool(self._current_person_id()))
        self.newButton.setEnabled(not busy)
        self.personBox.setEnabled(not busy)
        self.statusLabel.setText(text)

    def _submit(self):
        pid = self._current_person_id()
        text = self.inputEdit.toPlainText().strip()
        if not pid:
            QMessageBox.warning(self, "人物分析", "先选择或新建人物。")
            return
        if not text:
            QMessageBox.warning(self, "人物分析", "先输入观察、原话或聊天内容。")
            return

        source_kind = self._source_kind()
        platform = self._platform()
        relationship = str(self._current_person().get("relationship") or "")
        self._set_busy(True, "人物分析 Agent 正在整理这条资料…")

        def work():
            try:
                result = person_input_service.submit(
                    pid,
                    text,
                    source_kind=source_kind,
                    platform=platform,
                    relationship=relationship,
                    allow_intimacy=self.intimacyCheck.isChecked(),
                )
            except Exception as exc:
                self.analysisDone.emit(False, {}, str(exc))
                return
            self.analysisDone.emit(True, result, "")

        threading.Thread(target=work, daemon=True).start()

    def _analysis_finished(self, ok: bool, result: object, reason: str):
        self._set_busy(False, "")
        if not ok:
            QMessageBox.critical(self, "分析失败", reason)
            return
        self.inputEdit.clear()
        self._load_person()
        data = result if isinstance(result, dict) else {}
        self.statusLabel.setText(
            f"已保存：人物信息 {len(data.get('stored_memory_ids') or [])} 条，"
            f"亲密偏好 {len(data.get('stored_intimacy_ids') or [])} 条。"
        )

    def _generate_strategy(self):
        pid = self._current_person_id()
        if not pid:
            return
        person = self._current_person()
        self._set_busy(True, "正在根据全部人物资料生成互动攻略…")

        def work():
            try:
                data = strategy_service.generate_strategy_for_person(
                    pid,
                    relationship_setting=str(person.get("relationship") or ""),
                    include_intimacy=self.intimacyCheck.isChecked(),
                )
            except Exception as exc:
                self.strategyDone.emit(False, {}, str(exc))
                return
            self.strategyDone.emit(True, data, "")

        threading.Thread(target=work, daemon=True).start()

    def _strategy_finished(self, ok: bool, result: object, reason: str):
        self._set_busy(False, "")
        if not ok:
            QMessageBox.critical(self, "攻略生成失败", reason)
            return
        data = result if isinstance(result, dict) else {}
        self.strategyEdit.setPlainText(self._strategy_text(data))
        self.statusLabel.setText("互动攻略已刷新。")

    @staticmethod
    def _safe_name(value: str) -> str:
        value = re.sub(r'[\\/:*?"<>|]+', "_", str(value or "").strip())
        return value[:80] or "人物"

    def _export_current(self):
        pid = self._current_person_id()
        if not pid:
            return
        person = self._current_person()
        name = self._safe_name(person.get("display_name") or pid)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出当前人物完整档案",
            name + "-Jev人物档案.md",
            "Markdown 文件 (*.md)",
        )
        if not path:
            return
        try:
            saved = markdown_export_service.export_person_markdown(pid, path)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出完成", "已导出到：\n" + str(saved))

    def _export_all(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出全部人物档案",
            "Jev-全部人物档案.md",
            "Markdown 文件 (*.md)",
        )
        if not path:
            return
        try:
            saved = markdown_export_service.export_all_people_markdown(path)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出完成", "已导出到：\n" + str(saved))
