from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from echotype.services.history import HistoryStore
from echotype.services.injection import set_clipboard


class HistoryPage(QWidget):
    """Searchable transcript history that can be mounted by any app shell."""

    repaste_requested = Signal(str, object)
    status_message = Signal(str)

    COLUMNS = ("When", "Transcript", "Language / script", "Application", "Mode", "Words", "RTF")

    def __init__(self, store: HistoryStore | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store or HistoryStore()
        self._entries: dict[str, dict[str, Any]] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search transcript text…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        filters.addWidget(self.search, 2)

        self.date_filter = QComboBox()
        self.date_filter.addItem("Any date", 0)
        self.date_filter.addItem("Today", 1)
        self.date_filter.addItem("Past 7 days", 7)
        self.date_filter.addItem("Past 30 days", 30)
        self.date_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.date_filter)

        self.language_filter = self._filter_combo("Any language")
        self.application_filter = self._filter_combo("Any application")
        self.mode_filter = self._filter_combo("Any mode")
        filters.addWidget(self.language_filter)
        filters.addWidget(self.application_filter)
        filters.addWidget(self.mode_filter)
        layout.addLayout(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(
            1, self.table.horizontalHeader().ResizeMode.Stretch
        )
        for column in (0, 2, 3, 4, 5, 6):
            self.table.horizontalHeader().setSectionResizeMode(
                column, self.table.horizontalHeader().ResizeMode.ResizeToContents
            )
        self.table.itemSelectionChanged.connect(self._show_selection)
        splitter.addWidget(self.table)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(14, 0, 0, 0)
        detail_layout.setSpacing(10)
        self.detail_title = QLabel("Select a transcript")
        self.detail_title.setObjectName("HeroTitle")
        self.detail_meta = QLabel("")
        self.detail_meta.setObjectName("Muted")
        self.detail_meta.setWordWrap(True)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Transcript detail")
        self.editor.setEnabled(False)
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(self.detail_meta)
        detail_layout.addWidget(self.editor, 1)

        action_row = QHBoxLayout()
        for label, handler in (
            ("Copy", self.copy_selected),
            ("Repaste", self.repaste_selected),
            ("Save edit", self.save_edit),
            ("Delete", self.delete_selected),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            action_row.addWidget(button)
        detail_layout.addLayout(action_row)
        splitter.addWidget(detail)
        splitter.setSizes([760, 360])
        layout.addWidget(splitter, 1)

        footer = QHBoxLayout()
        self.summary = QLabel("")
        self.summary.setObjectName("Muted")
        footer.addWidget(self.summary)
        footer.addStretch(1)
        export_button = QPushButton("Export…")
        export_button.clicked.connect(self.export_visible)
        footer.addWidget(export_button)
        clear_button = QPushButton("Clear history")
        clear_button.clicked.connect(self.clear_history)
        footer.addWidget(clear_button)
        layout.addLayout(footer)

        self.empty_label = QLabel(
            "No local transcripts yet. Dictation history will appear here when history is enabled."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setObjectName("Muted")
        layout.addWidget(self.empty_label)

    def _filter_combo(self, label: str) -> QComboBox:
        combo = QComboBox()
        combo.addItem(label, "")
        combo.currentIndexChanged.connect(self.refresh)
        return combo

    @staticmethod
    def _choice(item: dict[str, Any], *keys: str) -> str:
        return str(next((item.get(key) for key in keys if item.get(key)), ""))

    def _populate_filter(self, combo: QComboBox, label: str, values: set[str]) -> None:
        selected = str(combo.currentData() or "")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(label, "")
        for value in sorted(values, key=str.casefold):
            combo.addItem(value, value)
        index = combo.findData(selected)
        combo.setCurrentIndex(max(index, 0))
        combo.blockSignals(False)

    def refresh(self, *_args: object, select_id: str | None = None) -> None:
        all_entries = self.store.recent(10_000)
        self._populate_filter(
            self.language_filter,
            "Any language",
            {
                self._choice(item, "language", "script")
                for item in all_entries
                if self._choice(item, "language", "script")
            },
        )
        self._populate_filter(
            self.application_filter,
            "Any application",
            {
                self._choice(item, "target", "application")
                for item in all_entries
                if self._choice(item, "target", "application")
            },
        )
        self._populate_filter(
            self.mode_filter,
            "Any mode",
            {self._choice(item, "mode") for item in all_entries if self._choice(item, "mode")},
        )

        days = int(self.date_filter.currentData() or 0)
        date_from = (
            datetime.now().astimezone().date() - timedelta(days=max(days - 1, 0)) if days else None
        )
        entries = self.store.query(
            text=self.search.text(),
            date_from=date_from,
            language=str(self.language_filter.currentData() or ""),
            application=str(self.application_filter.currentData() or ""),
            mode=str(self.mode_filter.currentData() or ""),
        )
        self._entries = {str(entry["id"]): entry for entry in entries}
        self.table.setRowCount(len(entries))
        selected_row = -1
        for row, entry in enumerate(entries):
            timestamp = self._format_time(entry.get("time"))
            preview = " ".join(str(entry.get("text") or "").split())
            if len(preview) > 110:
                preview = preview[:107] + "…"
            values = (
                timestamp,
                preview,
                self._choice(entry, "language", "script") or "—",
                self._choice(entry, "target", "application") or "—",
                self._choice(entry, "mode") or "—",
                str(entry.get("word_count", "—")),
                f"{entry['rtf']:.2f}" if isinstance(entry.get("rtf"), (int, float)) else "—",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, entry["id"])
                self.table.setItem(row, column, cell)
            if entry["id"] == select_id:
                selected_row = row
        self.summary.setText(f"{len(entries)} of {len(all_entries)} transcripts")
        self.empty_label.setVisible(not entries)
        self.table.setVisible(bool(entries))
        if entries:
            self.table.selectRow(max(selected_row, 0))
        else:
            self._clear_detail()

    @staticmethod
    def _format_time(value: object) -> str:
        from datetime import datetime

        try:
            return datetime.fromtimestamp(float(value)).astimezone().strftime("%d %b %Y, %H:%M")
        except (TypeError, ValueError, OSError):
            return "Unknown time"

    def selected_entry(self) -> dict[str, Any] | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return self._entries.get(str(item.data(Qt.ItemDataRole.UserRole))) if item else None

    def _show_selection(self) -> None:
        entry = self.selected_entry()
        if entry is None:
            self._clear_detail()
            return
        self.detail_title.setText(self._format_time(entry.get("time")))
        metadata = []
        for label, key in (
            ("Language", "language"),
            ("Script", "script"),
            ("Mode", "mode"),
            ("Application", "target"),
            ("Words", "word_count"),
            ("Latency", "elapsed"),
            ("RTF", "rtf"),
            ("Audio", "audio_seconds"),
        ):
            value = entry.get(key)
            if value not in (None, ""):
                suffix = (
                    "s"
                    if key in {"elapsed", "audio_seconds"} and isinstance(value, (int, float))
                    else ""
                )
                metadata.append(
                    f"{label}: {value:.2f}{suffix}"
                    if isinstance(value, float)
                    else f"{label}: {value}{suffix}"
                )
        self.detail_meta.setText("  •  ".join(metadata))
        self.editor.setEnabled(True)
        self.editor.setPlainText(str(entry.get("text") or ""))

    def _clear_detail(self) -> None:
        self.detail_title.setText("Select a transcript")
        self.detail_meta.clear()
        self.editor.clear()
        self.editor.setEnabled(False)

    def copy_selected(self) -> None:
        entry = self.selected_entry()
        if entry and set_clipboard(str(entry["text"])):
            self.status_message.emit("Transcript copied")

    def repaste_selected(self) -> None:
        entry = self.selected_entry()
        if not entry:
            return
        text = str(entry["text"])
        set_clipboard(text)
        self.repaste_requested.emit(text, dict(entry))
        self.status_message.emit("Repaste requested; transcript also copied")

    def save_edit(self) -> None:
        entry = self.selected_entry()
        if not entry:
            return
        updated = self.store.update(str(entry["id"]), self.editor.toPlainText())
        if updated:
            self.refresh(select_id=str(entry["id"]))
            self.status_message.emit("Transcript updated")

    def delete_selected(self) -> None:
        entry = self.selected_entry()
        if not entry:
            return
        answer = QMessageBox.question(
            self, "Delete transcript?", "This removes the selected local transcript."
        )
        if answer == QMessageBox.StandardButton.Yes and self.store.delete(str(entry["id"])):
            self.refresh()
            self.status_message.emit("Transcript deleted")

    def clear_history(self) -> None:
        if not self.store.recent(1):
            return
        answer = QMessageBox.warning(
            self,
            "Clear all history?",
            "This permanently deletes every locally stored transcript. This cannot be undone.",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.store.clear()
            self.refresh()
            self.status_message.emit("History cleared")

    def export_visible(self) -> None:
        entries = list(self._entries.values())
        if not entries:
            return
        filename, selected_filter = QFileDialog.getSaveFileName(
            self, "Export transcript history", "echotype-history.txt", "Text (*.txt);;CSV (*.csv)"
        )
        if not filename:
            return
        csv_format = selected_filter.startswith("CSV") or Path(filename).suffix.casefold() == ".csv"
        Path(filename).write_text(
            self.store.export_csv(entries) if csv_format else self.store.export_text(entries),
            encoding="utf-8-sig" if csv_format else "utf-8",
        )
        self.status_message.emit(f"History exported to {filename}")
