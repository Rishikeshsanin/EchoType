from __future__ import annotations

from PySide6.QtCore import QEvent, QStringListModel, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QCompleter, QLabel, QVBoxLayout, QWidget

from echotype.core.languages import AUTO, LANGUAGES, name_for_code, script_for_code, script_label

POPULAR_CODES = (
    "en",
    "hi",
    "te",
    "kn",
    "ta",
    "ml",
    "bn",
    "mr",
    "gu",
    "pa",
    "or",
    "as",
)


class DropdownComboBox(QComboBox):
    """Editable combo that still reads and behaves like an obvious dropdown."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.showPopup()
            self.lineEdit().selectAll()
            return True
        return super().eventFilter(watched, event)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = self.palette().color(self.foregroundRole())
        color.setAlpha(230)
        painter.setPen(QPen(color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        center_x = self.width() - 17
        center_y = self.height() // 2
        painter.drawLine(center_x - 4, center_y - 2, center_x, center_y + 2)
        painter.drawLine(center_x, center_y + 2, center_x + 4, center_y - 2)


class LanguageSelector(QWidget):
    """Searchable, grouped selector backed by the complete language catalog."""

    language_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LanguageSelector")
        self.setMinimumWidth(250)
        self._committed_code = AUTO

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        label = QLabel("DICTATION LANGUAGE")
        label.setObjectName("Eyebrow")
        layout.addWidget(label)

        self.combo = DropdownComboBox()
        self.combo.setObjectName("LanguageCombo")
        self.combo.setAccessibleName("Dictation language")
        self.combo.setAccessibleDescription(
            "Search or open the dropdown to choose a language. Auto-detect is first."
        )
        self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo.setMaxVisibleItems(20)
        self.combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.combo.setMinimumContentsLength(23)
        self.combo.lineEdit().setPlaceholderText("Search languages…")
        self.combo.lineEdit().setClearButtonEnabled(True)

        catalog = {item[0]: item for item in LANGUAGES}
        self._add_language(catalog[AUTO])
        self._add_separator()
        self._add_header("POPULAR")
        for code in POPULAR_CODES:
            self._add_language(catalog[code])
        self._add_separator()
        self._add_header("ALL LANGUAGES")
        grouped = {AUTO, *POPULAR_CODES}
        for item in sorted(
            (item for item in LANGUAGES if item[0] not in grouped), key=lambda value: value[1]
        ):
            self._add_language(item)

        names = [name for _code, name, _script, _primary in LANGUAGES]
        completer = QCompleter(QStringListModel(names, self.combo), self.combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.activated.connect(self._select_name)
        self.combo.setCompleter(completer)
        self.combo.activated.connect(self._on_activated)
        self.combo.lineEdit().editingFinished.connect(self._accept_typed_name)
        layout.addWidget(self.combo)

        self.hint = QLabel()
        self.hint.setObjectName("FieldHint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.set_language(AUTO)

    def _add_separator(self) -> None:
        self.combo.insertSeparator(self.combo.count())

    def _add_header(self, text: str) -> None:
        self.combo.addItem(text)
        item = self.combo.model().item(self.combo.count() - 1)
        if item is not None:
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(QColor("#7f8996"))

    def _add_language(self, item: tuple[str, str, str | None, bool]) -> None:
        code, name, _script, _primary = item
        self.combo.addItem(name, code)

    @property
    def language_code(self) -> str:
        return self._committed_code

    def set_language(self, code: str) -> None:
        target = str(code or AUTO)
        index = self.combo.findData(target)
        if index < 0:
            target = AUTO
            index = self.combo.findData(AUTO)
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(index)
        self.combo.blockSignals(False)
        self._committed_code = target
        self._update_hint()

    def _on_activated(self, index: int) -> None:
        code = self.combo.itemData(index)
        if not code:
            return
        self._committed_code = str(code)
        self._update_hint()
        self.language_changed.emit(self._committed_code)

    def _select_name(self, name: str) -> None:
        for index in range(self.combo.count()):
            if self.combo.itemText(index).casefold() == str(name).casefold():
                self.combo.setCurrentIndex(index)
                self._on_activated(index)
                return

    def _accept_typed_name(self) -> None:
        typed = self.combo.currentText().strip()
        for index in range(self.combo.count()):
            if self.combo.itemText(index).casefold() == typed.casefold() and self.combo.itemData(
                index
            ):
                self.combo.setCurrentIndex(index)
                self._on_activated(index)
                return
        # Invalid searches never become settings values. Restore the last
        # committed selection instead of silently choosing another language.
        self.set_language(self._committed_code)

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
