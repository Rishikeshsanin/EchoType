from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class TermDialog(QDialog):
    def __init__(self, parent=None, *, term: str = "", aliases: list[str] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vocabulary term")
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        explanation = QLabel(
            "The preferred spelling replaces any matching alias during local Smart/Notes cleanup."
        )
        explanation.setObjectName("Muted")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        form = QFormLayout()
        self.term = QLineEdit(term)
        self.term.setPlaceholderText("Preferred spelling, e.g. PyTorch")
        self.aliases = QLineEdit(", ".join(aliases or []))
        self.aliases.setPlaceholderText("Comma-separated, e.g. pie torch, py torch")
        form.addRow("Preferred term", self.term)
        form.addRow("Spoken aliases", self.aliases)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, list[str]]:
        return self.term.text(), [alias.strip() for alias in self.aliases.text().split(",")]


class VocabularyPage(QWidget):
    """Searchable CRUD interface for persisted, active vocabulary profiles."""

    def __init__(self, vocabulary) -> None:
        super().__init__()
        self.vocabulary = vocabulary
        self._visible_terms: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        intro = QLabel(
            "Teach EchoType product names, technical terms, and preferred spellings. The active "
            "profile is applied locally to every Smart or Notes transcript."
        )
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        profile_card = QFrame()
        profile_card.setObjectName("SettingsCard")
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("VOCABULARY PROFILE")
        title.setObjectName("SectionTitle")
        profile_layout.addWidget(title)
        row = QHBoxLayout()
        self.profiles = QComboBox()
        self.profiles.currentIndexChanged.connect(self._profile_changed)
        self.active_status = QLabel()
        self.active_status.setObjectName("StatusChip")
        activate = QPushButton("Activate")
        activate.clicked.connect(self._activate_profile)
        create = QPushButton("New profile")
        create.clicked.connect(self._create_profile)
        rename = QPushButton("Rename")
        rename.clicked.connect(self._rename_profile)
        delete = QPushButton("Delete")
        delete.setObjectName("DangerButton")
        delete.clicked.connect(self._delete_profile)
        row.addWidget(self.profiles, 1)
        row.addWidget(self.active_status)
        row.addWidget(activate)
        row.addWidget(create)
        row.addWidget(rename)
        row.addWidget(delete)
        profile_layout.addLayout(row)
        layout.addWidget(profile_card)

        terms_card = QFrame()
        terms_card.setObjectName("SettingsCard")
        terms_layout = QVBoxLayout(terms_card)
        terms_layout.setContentsMargins(20, 18, 20, 20)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search terms or aliases…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refresh_terms)
        add = QPushButton("Add term")
        add.setObjectName("PrimaryButton")
        add.clicked.connect(self._add_term)
        edit = QPushButton("Edit")
        edit.clicked.connect(self._edit_term)
        remove = QPushButton("Delete")
        remove.setObjectName("DangerButton")
        remove.clicked.connect(self._delete_term)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(add)
        toolbar.addWidget(edit)
        toolbar.addWidget(remove)
        terms_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Preferred term / replacement", "Spoken aliases"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(lambda _index: self._edit_term())
        terms_layout.addWidget(self.table, 1)
        self.summary = QLabel()
        self.summary.setObjectName("Muted")
        terms_layout.addWidget(self.summary)
        layout.addWidget(terms_card, 1)
        self._refresh_profiles()

    def _profile_id(self) -> str:
        return str(self.profiles.currentData() or "")

    def _refresh_profiles(self, selected: str | None = None) -> None:
        selected = selected or self._profile_id() or self.vocabulary.active_profile_id
        self.profiles.blockSignals(True)
        self.profiles.clear()
        for profile in self.vocabulary.profiles():
            marker = "● " if profile["id"] == self.vocabulary.active_profile_id else ""
            self.profiles.addItem(marker + profile["name"], profile["id"])
        index = self.profiles.findData(selected)
        self.profiles.setCurrentIndex(max(index, 0))
        self.profiles.blockSignals(False)
        self._profile_changed()

    def _profile_changed(self) -> None:
        active = self._profile_id() == self.vocabulary.active_profile_id
        self.active_status.setText("ACTIVE" if active else "INACTIVE")
        self._refresh_terms()

    def _refresh_terms(self) -> None:
        profile_id = self._profile_id()
        if not profile_id:
            return
        self._visible_terms = self.vocabulary.search(self.search.text(), profile_id)
        self.table.setRowCount(len(self._visible_terms))
        for row, entry in enumerate(self._visible_terms):
            term = QTableWidgetItem(entry["term"])
            term.setData(Qt.ItemDataRole.UserRole, entry["id"])
            aliases = QTableWidgetItem(", ".join(entry["aliases"]) or "—")
            self.table.setItem(row, 0, term)
            self.table.setItem(row, 1, aliases)
        total = len(self.vocabulary.get_profile(profile_id)["terms"])
        self.summary.setText(
            f"Showing {len(self._visible_terms)} of {total} term(s). Changes are saved locally and apply immediately."
        )

    def _selected_term(self) -> dict | None:
        row = self.table.currentRow()
        if 0 <= row < len(self._visible_terms):
            return self._visible_terms[row]
        return None

    def _show_error(self, exc: Exception) -> None:
        QMessageBox.warning(self, "Vocabulary", str(exc))

    def _create_profile(self) -> None:
        name, accepted = QInputDialog.getText(self, "New profile", "Profile name")
        if not accepted:
            return
        try:
            profile = self.vocabulary.create_profile(name)
            self._refresh_profiles(profile["id"])
        except (OSError, ValueError) as exc:
            self._show_error(exc)

    def _rename_profile(self) -> None:
        profile = self.vocabulary.get_profile(self._profile_id())
        name, accepted = QInputDialog.getText(
            self, "Rename profile", "Profile name", text=profile["name"]
        )
        if not accepted:
            return
        try:
            self.vocabulary.rename_profile(profile["id"], name)
            self._refresh_profiles(profile["id"])
        except (OSError, ValueError) as exc:
            self._show_error(exc)

    def _delete_profile(self) -> None:
        profile = self.vocabulary.get_profile(self._profile_id())
        answer = QMessageBox.question(
            self,
            "Delete vocabulary profile?",
            f"Delete “{profile['name']}” and all {len(profile['terms'])} of its terms?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.vocabulary.delete_profile(profile["id"])
            self._refresh_profiles(self.vocabulary.active_profile_id)
        except (OSError, ValueError) as exc:
            self._show_error(exc)

    def _activate_profile(self) -> None:
        try:
            self.vocabulary.activate_profile(self._profile_id())
            self._refresh_profiles(self._profile_id())
        except (OSError, KeyError) as exc:
            self._show_error(exc)

    def _add_term(self) -> None:
        dialog = TermDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        term, aliases = dialog.values()
        try:
            self.vocabulary.add_term(self._profile_id(), term, aliases)
            self._refresh_terms()
        except (OSError, ValueError) as exc:
            self._show_error(exc)

    def _edit_term(self) -> None:
        entry = self._selected_term()
        if entry is None:
            return
        dialog = TermDialog(self, term=entry["term"], aliases=entry["aliases"])
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        term, aliases = dialog.values()
        try:
            self.vocabulary.edit_term(self._profile_id(), entry["id"], term, aliases)
            self._refresh_terms()
        except (OSError, ValueError) as exc:
            self._show_error(exc)

    def _delete_term(self) -> None:
        entry = self._selected_term()
        if entry is None:
            return
        answer = QMessageBox.question(
            self, "Delete term?", f"Delete “{entry['term']}” from this profile?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.vocabulary.delete_term(self._profile_id(), entry["id"])
            self._refresh_terms()
        except (OSError, KeyError) as exc:
            self._show_error(exc)
