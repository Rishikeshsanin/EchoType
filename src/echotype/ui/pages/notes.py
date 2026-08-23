from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from echotype.services.history import HistoryStore
from echotype.services.notes import NotesStore


class NotesPage(QWidget):
    """Local Markdown-friendly notes editor with safe autosave."""

    status_message = Signal(str)
    note_saved = Signal(object)

    def __init__(
        self,
        store: NotesStore | None = None,
        history_store: HistoryStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store or NotesStore()
        self.history_store = history_store or HistoryStore()
        self._current_id: str | None = None
        self._loading = False
        self._autosave = QTimer(self)
        self._autosave.setSingleShot(True)
        self._autosave.setInterval(650)
        self._autosave.timeout.connect(self.save_current)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search notes…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)
        for label, handler in (
            ("New note", self.new_note),
            ("Latest transcript → note", self.send_latest_transcript),
            ("Duplicate", self.duplicate_current),
            ("Export…", self.export_current),
            ("Delete", self.delete_current),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            toolbar.addWidget(button)
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.notes_list = QListWidget()
        self.notes_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.notes_list.currentItemChanged.connect(self._select_item)
        splitter.addWidget(self.notes_list)

        editor_panel = QWidget()
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(14, 0, 0, 0)
        self.title = QLineEdit()
        self.title.setPlaceholderText("Note title")
        self.body = QPlainTextEdit()
        self.body.setPlaceholderText("Write a note. Markdown is welcome.")
        self.body.setTabChangesFocus(False)
        self.meta = QLabel("")
        self.meta.setObjectName("Muted")
        editor_layout.addWidget(self.title)
        editor_layout.addWidget(self.body, 1)
        editor_layout.addWidget(self.meta)

        save_row = QHBoxLayout()
        self.save_state = QLabel("Saved locally")
        self.save_state.setObjectName("Muted")
        save_row.addWidget(self.save_state)
        save_row.addStretch(1)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_current)
        save_row.addWidget(save_button)
        editor_layout.addLayout(save_row)
        splitter.addWidget(editor_panel)
        splitter.setSizes([300, 800])
        layout.addWidget(splitter, 1)

        self.empty = QLabel("No notes yet. Create one or send the latest transcript here.")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setObjectName("Muted")
        layout.addWidget(self.empty)

        self.title.textChanged.connect(self._schedule_save)
        self.body.textChanged.connect(self._schedule_save)
        self._set_editor_enabled(False)

    def _set_editor_enabled(self, enabled: bool) -> None:
        self.title.setEnabled(enabled)
        self.body.setEnabled(enabled)

    def refresh(self, *_args: object, select_id: str | None = None) -> None:
        target_id = select_id or self._current_id
        notes = self.store.list(self.search.text())
        self.notes_list.blockSignals(True)
        self.notes_list.clear()
        selected_item = None
        for note in notes:
            updated = (
                datetime.fromtimestamp(float(note["updated_at"]))
                .astimezone()
                .strftime("%d %b, %H:%M")
            )
            preview = " ".join(str(note["body"]).split())[:80]
            item = QListWidgetItem(f"{note['title']}\n{preview or 'Empty note'}\n{updated}")
            item.setData(Qt.ItemDataRole.UserRole, note["id"])
            self.notes_list.addItem(item)
            if note["id"] == target_id:
                selected_item = item
        self.notes_list.blockSignals(False)
        self.empty.setVisible(not notes)
        self.notes_list.setVisible(bool(notes))
        if selected_item is not None:
            self.notes_list.setCurrentItem(selected_item)
        elif notes:
            self.notes_list.setCurrentRow(0)
        else:
            self._load_note(None)

    def _select_item(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if self._autosave.isActive():
            self.save_current(refresh=False)
        note_id = str(current.data(Qt.ItemDataRole.UserRole)) if current else None
        self._load_note(self.store.get(note_id) if note_id else None)

    def _load_note(self, note: dict[str, Any] | None) -> None:
        self._loading = True
        self._autosave.stop()
        self._current_id = str(note["id"]) if note else None
        self.title.setText(str(note["title"]) if note else "")
        self.body.setPlainText(str(note["body"]) if note else "")
        self._set_editor_enabled(note is not None)
        self._update_meta(note)
        self.save_state.setText("Saved locally" if note else "")
        self._loading = False

    def _update_meta(self, note: dict[str, Any] | None = None) -> None:
        if note is None and self._current_id:
            note = self.store.get(self._current_id)
        if not note:
            self.meta.clear()
            return
        created = (
            datetime.fromtimestamp(float(note["created_at"]))
            .astimezone()
            .strftime("%d %b %Y, %H:%M")
        )
        words = len(self.body.toPlainText().split())
        self.meta.setText(f"Created {created}  •  {words} words  •  Stored only on this device")

    def _schedule_save(self) -> None:
        if self._loading or not self._current_id:
            return
        self.save_state.setText("Unsaved changes…")
        self._update_meta()
        self._autosave.start()

    def new_note(self) -> None:
        note = self.store.create()
        self.search.clear()
        self.refresh(select_id=str(note["id"]))
        self.title.setFocus()
        self.title.selectAll()

    def save_current(self, *, refresh: bool = True) -> None:
        if self._loading or not self._current_id:
            return
        self._autosave.stop()
        note = self.store.update(
            self._current_id,
            title=self.title.text(),
            body=self.body.toPlainText(),
        )
        if note:
            self.save_state.setText("Saved locally")
            self.note_saved.emit(dict(note))
            if refresh:
                self.refresh(select_id=self._current_id)

    def duplicate_current(self) -> None:
        if not self._current_id:
            return
        self.save_current(refresh=False)
        note = self.store.duplicate(self._current_id)
        if note:
            self.search.clear()
            self.refresh(select_id=str(note["id"]))
            self.status_message.emit("Note duplicated")

    def delete_current(self) -> None:
        if not self._current_id:
            return
        answer = QMessageBox.question(
            self, "Delete note?", "This permanently deletes the selected local note."
        )
        if answer == QMessageBox.StandardButton.Yes and self.store.delete(self._current_id):
            self._current_id = None
            self.refresh()
            self.status_message.emit("Note deleted")

    @Slot()
    def send_latest_transcript(self) -> None:
        latest = self.history_store.recent(1)
        if not latest:
            self.status_message.emit("No saved transcript is available")
            return
        note = self.store.create_from_transcript(latest[0])
        self.search.clear()
        self.refresh(select_id=str(note["id"]))
        self.status_message.emit("Latest transcript sent to Notes")

    @Slot(str, object)
    def receive_transcript(self, text: str, metadata: object = None) -> None:
        """Clean target for DictationRuntime.transcript_ready."""
        data = metadata if isinstance(metadata, dict) else {}
        note = self.store.receive_dictation(text, metadata=data)
        self.search.clear()
        self.refresh(select_id=str(note["id"]))
        self.status_message.emit("Dictation received in Notes")

    def export_current(self) -> None:
        if not self._current_id:
            return
        self.save_current(refresh=False)
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export note",
            f"{self.title.text().strip() or 'echotype-note'}.md",
            "Markdown (*.md);;Text (*.txt)",
        )
        if not filename:
            return
        text_format = (
            selected_filter.startswith("Text") or Path(filename).suffix.casefold() == ".txt"
        )
        content = (
            self.store.export_text(self._current_id)
            if text_format
            else self.store.export_markdown(self._current_id)
        )
        Path(filename).write_text(content, encoding="utf-8")
        self.status_message.emit(f"Note exported to {filename}")
