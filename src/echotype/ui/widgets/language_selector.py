from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QCompleter, QLabel, QVBoxLayout, QWidget

from echotype.core.languages import AUTO, LANGUAGES, name_for_code, script_for_code, script_label


class LanguageSelector(QWidget):
    """Searchable selector backed by the complete language catalog."""

    language_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LanguageSelector")
        self.setMinimumWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        label = QLabel("DICTATION LANGUAGE")
        label.setObjectName("Eyebrow")
        layout.addWidget(label)

        self.combo = QComboBox()
        self.combo.setObjectName("LanguageCombo")
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo.setMaxVisibleItems(18)
        self.combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.combo.setMinimumContentsLength(19)
        self.combo.lineEdit().setPlaceholderText("Search languages…")

        auto = next(item for item in LANGUAGES if item[0] == AUTO)
        primary = sorted(
            (item for item in LANGUAGES if item[3] and item[0] != AUTO), key=lambda x: x[1]
        )
        regional = sorted((item for item in LANGUAGES if not item[3]), key=lambda x: x[1])
        self._add_language(auto)
        self.combo.insertSeparator(self.combo.count())
        for item in primary:
            self._add_language(item)
        self.combo.insertSeparator(self.combo.count())
        for item in regional:
            self._add_language(item)

        completer = QCompleter(self.combo.model(), self.combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.combo.setCompleter(completer)
        self.combo.activated.connect(self._on_activated)
        self.combo.lineEdit().editingFinished.connect(self._accept_typed_name)
        layout.addWidget(self.combo)

        self.hint = QLabel()
        self.hint.setObjectName("FieldHint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.set_language(AUTO)

    def _add_language(self, item: tuple[str, str, str | None, bool]) -> None:
        code, name, _script, _primary = item
        self.combo.addItem(name, code)

    @property
    def language_code(self) -> str:
        value = self.combo.currentData()
        return str(value) if value else AUTO

    def set_language(self, code: str) -> None:
        target = str(code or AUTO)
        index = self.combo.findData(target)
        if index < 0:
            index = self.combo.findData(AUTO)
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(index)
        self.combo.blockSignals(False)
        self._update_hint()

    def _on_activated(self, index: int) -> None:
        code = self.combo.itemData(index)
        if not code:
            return
        self._update_hint()
        self.language_changed.emit(str(code))

    def _accept_typed_name(self) -> None:
        typed = self.combo.currentText().strip()
        for index in range(self.combo.count()):
            if self.combo.itemText(index).casefold() == typed.casefold() and self.combo.itemData(
                index
            ):
                self.combo.setCurrentIndex(index)
                self._on_activated(index)
                return
        self.set_language(self.language_code)

    def _update_hint(self) -> None:
        code = self.language_code
        if code == AUTO:
            self.hint.setText(
                "Auto-detect uses script evidence; it does not claim a language from script alone."
            )
            return
        script = script_label(script_for_code(code))
        self.hint.setText(
            f"{name_for_code(code)} selected · decoder constrained to {script} script"
        )
