from __future__ import annotations

from PySide6.QtCore import Qt
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
    """Initial EchoType V2 shell.

    The shell is intentionally UI-only. Speech, hotkey, history, and Windows
    injection services will be adapted behind explicit service interfaces
    rather than being coupled directly to widgets.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EchoType")
        self.resize(1280, 820)
        self.setMinimumSize(960, 640)

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
            page = self._build_dictate_page() if key == "dictate" else self._build_placeholder_page(title, key)
            self.page_index[key] = self.pages.addWidget(page)
        content_layout.addWidget(self.pages, 1)

        outer.addWidget(content, 1)

        self.statusBar().showMessage("V2 UI foundation • speech engine migration pending")
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

        offline = QLabel("OFFLINE")
        offline.setObjectName("StatusChip")
        row.addWidget(offline)

        compute = QLabel("ENGINE NOT CONNECTED")
        compute.setObjectName("StatusChip")
        row.addWidget(compute)

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

        state = QLabel("READY FOR THE NEW ENGINE")
        state.setObjectName("Muted")
        state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(state)

        title = QLabel("Your voice should feel like another keyboard.")
        title.setObjectName("HeroTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        hero_layout.addWidget(title)

        hint = QLabel(
            "The V2 interface is now separated from transcription. "
            "Next we migrate the proven offline speech, hotkey and cursor-injection pipeline behind services."
        )
        hint.setObjectName("Muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setMaximumWidth(720)
        hero_layout.addWidget(hint)

        mode_row = QHBoxLayout()
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        for index, name in enumerate(("Verbatim", "Smart", "Notes")):
            button = QPushButton(name)
            button.setObjectName("ModeButton")
            button.setCheckable(True)
            button.setChecked(index == 1)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            mode_group.addButton(button)
            mode_row.addWidget(button)
        hero_layout.addLayout(mode_row)

        record = QPushButton("Hold Right Shift to speak")
        record.setObjectName("PrimaryButton")
        record.setEnabled(False)
        record.setToolTip("Enabled after the V1 dictation engine is migrated into EchoType services.")
        hero_layout.addWidget(record, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(hero, 3)

        transcript_card = QFrame()
        transcript_card.setObjectName("Card")
        transcript_layout = QVBoxLayout(transcript_card)
        transcript_layout.setContentsMargins(22, 20, 22, 20)
        transcript_layout.setSpacing(10)

        label = QLabel("LATEST TRANSCRIPT")
        label.setObjectName("Muted")
        transcript_layout.addWidget(label)

        transcript = QPlainTextEdit()
        transcript.setReadOnly(True)
        transcript.setPlaceholderText("Your next transcript will appear here after the engine migration.")
        transcript.setMaximumBlockCount(1_000)
        transcript_layout.addWidget(transcript)

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
            "notes": "Local voice-assisted notes will live here.",
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
