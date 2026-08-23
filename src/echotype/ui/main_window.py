from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from echotype.ui.pages.dictate import DictatePage

NAV_ITEMS = (
    ("Dictate", "dictate"),
    ("Notes", "notes"),
    ("History", "history"),
    ("Vocabulary", "vocabulary"),
    ("Analytics", "analytics"),
    ("Settings", "settings"),
)


class MainWindow(QMainWindow):
    """Responsive EchoType shell; services remain behind Qt signals."""

    mode_changed = Signal(str)
    language_changed = Signal(str)
    record_pressed = Signal()
    record_released = Signal()
    paste_requested = Signal()
    clear_requested = Signal()

    def __init__(
        self,
        *,
        history_page: QWidget | None = None,
        notes_page: QWidget | None = None,
        settings_page: QWidget | None = None,
        vocabulary_page: QWidget | None = None,
        default_mode: str = "smart",
    ) -> None:
        super().__init__()
        self.setWindowTitle("EchoType")
        self.resize(1280, 800)
        self.setMinimumSize(940, 640)
        self._history_page = history_page
        self._notes_page = notes_page
        self._settings_page = settings_page
        self._vocabulary_page = vocabulary_page
        self._default_mode = default_mode

        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.sidebar = self._build_sidebar()
        outer.addWidget(self.sidebar)

        content = QWidget()
        content.setObjectName("ContentArea")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(24, 18, 24, 18)
        self.content_layout.setSpacing(12)
        self.content_layout.addLayout(self._build_topbar())

        self.pages = QStackedWidget()
        self.pages.setObjectName("PageStack")
        self.page_index: dict[str, int] = {}
        for title, key in NAV_ITEMS:
            if key == "dictate":
                page = self._build_dictate_page()
            elif key == "notes" and self._notes_page is not None:
                page = self._notes_page
            elif key == "notes":
                page = self._build_notes_page()
            elif key == "history" and self._history_page is not None:
                page = self._history_page
            elif key == "settings" and self._settings_page is not None:
                page = self._settings_page
            elif key == "vocabulary" and self._vocabulary_page is not None:
                page = self._vocabulary_page
            else:
                page = self._build_placeholder_page(title, key)
            self.page_index[key] = self.pages.addWidget(page)
        self.content_layout.addWidget(self.pages, 1)
        outer.addWidget(content, 1)

        self.statusBar().showMessage("Starting EchoType services…")
        self._select_page("dictate")

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(5)

        brand = QLabel("EchoType")
        brand.setObjectName("Brand")
        layout.addWidget(brand)

        tagline = QLabel("Local voice typing")
        tagline.setObjectName("Tagline")
        tagline.setWordWrap(True)
        layout.addWidget(tagline)
        layout.addSpacing(17)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        for title, key in NAV_ITEMS:
            button = QPushButton(title)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page_key=key: self._select_page(page_key))
            self.nav_group.addButton(button)
            self.nav_buttons[key] = button
            layout.addWidget(button)

        layout.addStretch(1)
        privacy = QLabel("LOCAL-FIRST\nAudio stays on this device")
        privacy.setObjectName("PrivacyMark")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        attribution = QLabel("Speech by SraVaani 1.0\nARTPARK-IISc · Sharadh Naidu")
        attribution.setObjectName("Attribution")
        attribution.setWordWrap(True)
        layout.addWidget(attribution)
        return sidebar

    def _build_topbar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(0)
        self.page_title = QLabel("Dictate")
        self.page_title.setObjectName("PageTitle")
        title_stack.addWidget(self.page_title)
        self.page_subtitle = QLabel("Fast, private dictation for every Windows app")
        self.page_subtitle.setObjectName("PageSubtitle")
        title_stack.addWidget(self.page_subtitle)
        row.addLayout(title_stack)
        row.addStretch(1)

        offline = QLabel("●  LOCAL")
        offline.setObjectName("LocalChip")
        row.addWidget(offline)

        self.compute_chip = QLabel("MODEL STARTING")
        self.compute_chip.setObjectName("StatusChip")
        self.compute_chip.setMinimumWidth(118)
        self.compute_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.compute_chip)
        return row

    def _build_dictate_page(self) -> DictatePage:
        self.dictate_page = DictatePage()
        self.dictate_page.mode_changed.connect(self.mode_changed)
        self.dictate_page.language_changed.connect(self.language_changed)
        self.dictate_page.record_pressed.connect(self.record_pressed)
        self.dictate_page.record_released.connect(self.record_released)
        self.dictate_page.paste_requested.connect(self.paste_requested)
        self.dictate_page.clear_requested.connect(self.clear_requested)
        self.dictate_page.notes_requested.connect(self._receive_note)
        self.dictate_page.notification.connect(self._notify)
        return self.dictate_page

    def _build_notes_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("NotesPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("Card")
        inner = QVBoxLayout(card)
        inner.setContentsMargins(20, 18, 20, 20)
        inner.setSpacing(10)
        title = QLabel("Voice notes scratchpad")
        title.setObjectName("PanelTitle")
        inner.addWidget(title)
        hint = QLabel(
            "Send a transcript here from Dictate. Notes remain in memory for this app session."
        )
        hint.setObjectName("FieldHint")
        inner.addWidget(hint)
        self.notes_editor = QPlainTextEdit()
        self.notes_editor.setObjectName("NotesEditor")
        self.notes_editor.setPlaceholderText("Your voice-assisted notes will appear here…")
        inner.addWidget(self.notes_editor, 1)
        layout.addWidget(card)
        return page

    def _build_placeholder_page(self, title: str, key: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("Card")
        inner = QVBoxLayout(card)
        inner.setContentsMargins(28, 28, 28, 28)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        heading = QLabel(title)
        heading.setObjectName("PanelTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(heading)

        descriptions = {
            "history": (
                "The Dictate page already shows a compact preview of locally stored transcripts."
            ),
            "vocabulary": (
                "Reusable terminology profiles will live here without changing the speech engine."
            ),
            "analytics": (
                "Private, on-device productivity detail will build on the live session scorecard."
            ),
            "settings": (
                "Audio, shortcuts, privacy, compute, and diagnostics will be integrated here."
            ),
        }
        copy = QLabel(descriptions.get(key, "Planned for EchoType V2."))
        copy.setObjectName("FieldHint")
        copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy.setWordWrap(True)
        copy.setMaximumWidth(620)
        inner.addWidget(copy)

        layout.addWidget(card)
        return page

    def _select_page(self, key: str) -> None:
        if key not in self.page_index:
            return
        self.pages.setCurrentIndex(self.page_index[key])
        self.nav_buttons[key].setChecked(True)
        title = next(title for title, page_key in NAV_ITEMS if page_key == key)
        self.page_title.setText(title)
        subtitles = {
            "dictate": "Fast, private dictation for every Windows app",
            "notes": "A local scratchpad for captured thoughts",
            "history": "Review local transcripts",
            "vocabulary": "Teach EchoType your terminology",
            "analytics": "Understand your dictation workflow",
            "settings": "Tune EchoType for this device",
        }
        self.page_subtitle.setText(subtitles.get(key, ""))

    def apply_runtime_snapshot(self, snapshot: dict[str, object]) -> None:
        self.dictate_page.apply_snapshot(snapshot)

    def set_engine_status(self, status: str, detail: str) -> None:
        labels = {
            "idle": "MODEL IDLE",
            "loading": "MODEL LOADING",
            "ready": detail.upper() if detail else "MODEL READY",
            "busy": "TRANSCRIBING",
            "failed": "MODEL ERROR",
        }
        self.compute_chip.setText(labels.get(status.lower(), status.upper()))
        self.compute_chip.setProperty("engineStatus", status.lower())
        self.compute_chip.style().unpolish(self.compute_chip)
        self.compute_chip.style().polish(self.compute_chip)
        self.dictate_page.set_engine_status(status, detail)

    def set_recording_state(self, state: str, detail: str) -> None:
        self.dictate_page.set_recording_state(state, detail)
        if detail:
            self.statusBar().showMessage(detail, 5_000)

    def set_audio_level(self, level: float, seconds: float) -> None:
        self.dictate_page.set_audio_level(level, seconds)

    def show_transcript(self, text: str, metadata: object) -> None:
        self.dictate_page.show_transcript(text, metadata)

    def show_warning(self, title: str, detail: str) -> None:
        self.statusBar().showMessage(f"{title}: {detail}", 10_000)

    def _receive_note(self, text: str) -> None:
        if self._notes_page is not None and hasattr(self._notes_page, "receive_transcript"):
            self._notes_page.receive_transcript(text, {"source": "dictate_action"})
            self._select_page("notes")
            self._notify("Transcript added to Notes")
            return
        existing = self.notes_editor.toPlainText().rstrip()
        self.notes_editor.setPlainText(f"{existing}\n\n{text}".strip())
        cursor = self.notes_editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.notes_editor.setTextCursor(cursor)
        self._select_page("notes")
        self._notify("Transcript added to Notes")

    def _notify(self, message: str) -> None:
        self.statusBar().showMessage(message, 5_000)

    def show_status(self, message: str) -> None:
        self._notify(message)

    def resizeEvent(self, event: QResizeEvent) -> None:
        compact = event.size().width() < 1080
        self.sidebar.setFixedWidth(176 if compact else 210)
        margin = 16 if compact else 24
        self.content_layout.setContentsMargins(margin, 16 if compact else 18, margin, 16)
        super().resizeEvent(event)
