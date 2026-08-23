from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

NAV_ITEMS = (
    ("Dictate", "dictate"),
    ("Notes", "notes"),
    ("History", "history"),
    ("Vocabulary", "vocabulary"),
    ("Analytics", "analytics"),
    ("Settings", "settings"),
)


class MainWindow(QMainWindow):
    """EchoType V2 shell connected to runtime through Qt signals only."""

    mode_changed = Signal(str)
    record_pressed = Signal()
    record_released = Signal()

    def __init__(
        self,
        *,
        settings_page: QWidget | None = None,
        vocabulary_page: QWidget | None = None,
        default_mode: str = "smart",
    ) -> None:
        super().__init__()
        self.setWindowTitle("EchoType")
        self.resize(1280, 820)
        self.setMinimumSize(960, 640)
        self._engine_ready = False
        self._settings_page = settings_page
        self._vocabulary_page = vocabulary_page
        self._default_mode = default_mode

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(34, 28, 34, 28)
        content_layout.setSpacing(20)
        content_layout.addLayout(self._build_topbar())

        self.pages = QStackedWidget()
        self.page_index: dict[str, int] = {}
        for title, key in NAV_ITEMS:
            if key == "dictate":
                page = self._build_dictate_page()
            elif key == "settings" and self._settings_page is not None:
                page = self._settings_page
            elif key == "vocabulary" and self._vocabulary_page is not None:
                page = self._vocabulary_page
            else:
                page = self._build_placeholder_page(title, key)
            self.page_index[key] = self.pages.addWidget(page)
        content_layout.addWidget(self.pages, 1)
        outer.addWidget(content, 1)

        self.statusBar().showMessage("Starting EchoType services…")
        self._select_page("dictate")

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(238)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 26, 20, 20)
        layout.setSpacing(8)

        brand = QLabel("EchoType")
        brand.setObjectName("Brand")
        layout.addWidget(brand)

        tagline = QLabel("Speak naturally. Type anywhere.")
        tagline.setObjectName("Tagline")
        tagline.setWordWrap(True)
        layout.addWidget(tagline)
        layout.addSpacing(22)

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
        privacy.setObjectName("Muted")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        return sidebar

    def _build_topbar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self.page_title = QLabel("Dictate")
        self.page_title.setObjectName("PageTitle")
        row.addWidget(self.page_title)
        row.addStretch(1)

        offline = QLabel("LOCAL")
        offline.setObjectName("StatusChip")
        row.addWidget(offline)

        self.compute_chip = QLabel("MODEL STARTING")
        self.compute_chip.setObjectName("StatusChip")
        row.addWidget(self.compute_chip)
        return row

    def _build_dictate_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("Card")
        hero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(34, 34, 34, 34)
        hero_layout.setSpacing(14)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.state_label = QLabel("STARTING")
        self.state_label.setObjectName("Muted")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self.state_label)

        self.hero_title = QLabel("Loading your offline speech engine…")
        self.hero_title.setObjectName("HeroTitle")
        self.hero_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hero_title.setWordWrap(True)
        hero_layout.addWidget(self.hero_title)

        self.hint_label = QLabel(
            "EchoType loads SraVaani locally. Once ready, hold Right Shift in any app, speak, then release."
        )
        self.hint_label.setObjectName("Muted")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        self.hint_label.setMaximumWidth(760)
        hero_layout.addWidget(self.hint_label)

        mode_row = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        for name in ("Verbatim", "Smart", "Notes"):
            mode_name = name.lower()
            button = QPushButton(name)
            button.setObjectName("ModeButton")
            button.setCheckable(True)
            button.setChecked(name.lower() == self._default_mode)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, selected=mode_name: self.mode_changed.emit(selected)
            )
            self.mode_group.addButton(button)
            mode_row.addWidget(button)
        hero_layout.addLayout(mode_row)

        self.record_button = QPushButton("Model loading…")
        self.record_button.setObjectName("PrimaryButton")
        self.record_button.setEnabled(False)
        self.record_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_button.pressed.connect(self.record_pressed.emit)
        self.record_button.released.connect(self.record_released.emit)
        hero_layout.addWidget(self.record_button, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hero, 3)

        transcript_card = QFrame()
        transcript_card.setObjectName("Card")
        transcript_layout = QVBoxLayout(transcript_card)
        transcript_layout.setContentsMargins(22, 20, 22, 20)
        transcript_layout.setSpacing(10)

        label_row = QHBoxLayout()
        label = QLabel("LATEST TRANSCRIPT")
        label.setObjectName("Muted")
        label_row.addWidget(label)
        label_row.addStretch(1)
        self.transcript_meta = QLabel("")
        self.transcript_meta.setObjectName("Muted")
        label_row.addWidget(self.transcript_meta)
        transcript_layout.addLayout(label_row)

        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("Your next transcript will appear here.")
        self.transcript.setMaximumBlockCount(1_000)
        transcript_layout.addWidget(self.transcript)
        layout.addWidget(transcript_card, 2)
        return page

    def _build_placeholder_page(self, title: str, key: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("Card")
        inner = QVBoxLayout(card)
        inner.setContentsMargins(34, 34, 34, 34)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        heading = QLabel(title)
        heading.setObjectName("HeroTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(heading)

        descriptions = {
            "notes": "Local voice-assisted notes are the next UI milestone after the Dictate loop is stable.",
            "history": "Search, filter, repaste, export and delete local transcripts here.",
            "vocabulary": "Create reusable terminology profiles for better recognition.",
            "analytics": "Local-only dictation performance and productivity metrics will appear here.",
            "settings": "Audio, languages, text modes, shortcuts, privacy, compute and diagnostics will live here.",
        }
        copy = QLabel(descriptions.get(key, "Planned for EchoType V2."))
        copy.setObjectName("Muted")
        copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy.setWordWrap(True)
        copy.setMaximumWidth(650)
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

    def set_engine_status(self, status: str, detail: str) -> None:
        status = status.lower()
        self._engine_ready = status in {"ready", "busy"}
        labels = {
            "idle": "MODEL IDLE",
            "loading": "MODEL LOADING",
            "ready": detail.upper() if detail else "MODEL READY",
            "busy": "TRANSCRIBING",
            "failed": "MODEL ERROR",
        }
        self.compute_chip.setText(labels.get(status, status.upper()))
        if status == "loading":
            self.state_label.setText("LOADING")
            self.hero_title.setText("Loading your offline speech engine…")
        elif status == "failed":
            self.state_label.setText("ENGINE ERROR")
            self.hero_title.setText("EchoType could not load the speech model.")
            self.hint_label.setText(detail or "Check the status message and model setup.")
        self.record_button.setEnabled(self._engine_ready)
        if self._engine_ready and self.record_button.text() == "Model loading…":
            self.record_button.setText("Hold to speak")

    def set_recording_state(self, state: str, detail: str) -> None:
        state = state.lower()
        if state == "listening":
            self.state_label.setText("LISTENING")
            self.hero_title.setText("Speak naturally.")
            self.hint_label.setText(
                f"Text will return to: {detail}" if detail else "Release to transcribe."
            )
            self.record_button.setText("Release to transcribe")
        elif state == "processing":
            self.state_label.setText("PROCESSING")
            self.hero_title.setText("Turning speech into text…")
            self.hint_label.setText(detail)
            self.record_button.setEnabled(False)
            self.record_button.setText("Processing…")
        elif state == "loading":
            self.state_label.setText("LOADING")
            self.hint_label.setText(detail)
        else:
            self.state_label.setText("READY" if self._engine_ready else "STARTING")
            self.hero_title.setText(
                "Your voice is another keyboard."
                if self._engine_ready
                else "Loading your offline speech engine…"
            )
            self.hint_label.setText(detail or "Hold Right Shift in any app, speak, then release.")
            self.record_button.setEnabled(self._engine_ready)
            self.record_button.setText("Hold to speak" if self._engine_ready else "Model loading…")
        self.statusBar().showMessage(detail, 5_000)

    def show_transcript(self, text: str, metadata: object) -> None:
        self.transcript.setPlainText(text)
        data = metadata if isinstance(metadata, dict) else {}
        bits = []
        mode = data.get("mode")
        if mode:
            bits.append(str(mode).upper())
        rtf = data.get("rtf")
        if isinstance(rtf, (int, float)):
            bits.append(f"RTF {rtf:.2f}")
        device = data.get("device")
        if device:
            bits.append(str(device).upper())
        self.transcript_meta.setText("  •  ".join(bits))

    def show_warning(self, title: str, detail: str) -> None:
        self.statusBar().showMessage(f"{title}: {detail}", 10_000)
