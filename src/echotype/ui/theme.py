"""Shared EchoType visual tokens and native Qt stylesheet."""

BG = "#0a0c0f"
SIDEBAR = "#0e1115"
SURFACE = "#12161b"
SURFACE_RAISED = "#181d24"
SURFACE_ACTIVE = "#20262f"
BORDER = "#2a313b"
BORDER_STRONG = "#3a4552"
TEXT = "#f3f6f9"
TEXT_SOFT = "#bdc6d1"
TEXT_MUTED = "#7f8996"
ACCENT = "#e5ebf2"
ACCENT_TEXT = "#0b0e12"
SUCCESS = "#6dd6a0"
WARNING = "#e3b669"
ERROR = "#ee7c82"


def stylesheet() -> str:
    """Return the application QSS.

    Labels are explicitly transparent. This avoids the opaque rectangular
    backgrounds Qt can inherit when a broad QWidget background rule is used.
    """
    return f"""
    QWidget {{
        color: {TEXT};
        font-family: "Segoe UI Variable", "Segoe UI", "Nirmala UI", sans-serif;
        font-size: 13px;
    }}

    QMainWindow, QWidget#AppRoot, QWidget#ContentArea, QStackedWidget#PageStack,
    QWidget#DictatePage, QWidget#NotesPage, QWidget#RightRail {{
        background-color: {BG};
    }}

    QLabel {{
        background-color: transparent;
        border: none;
    }}

    QFrame#Sidebar {{
        background-color: {SIDEBAR};
        border: none;
        border-right: 1px solid {BORDER};
    }}

    QLabel#Brand {{
        color: {TEXT};
        font-size: 23px;
        font-weight: 700;
    }}

    QLabel#Tagline, QLabel#PageSubtitle, QLabel#FieldHint {{
        color: {TEXT_MUTED};
    }}

    QLabel#Tagline {{
        font-size: 12px;
    }}

    QLabel#PageTitle {{
        font-size: 23px;
        font-weight: 700;
    }}

    QLabel#PageSubtitle {{
        font-size: 12px;
    }}

    QLabel#PanelTitle {{
        font-size: 18px;
        font-weight: 650;
    }}

    QLabel#Eyebrow, QLabel#StatLabel {{
        color: {TEXT_MUTED};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1px;
    }}

    QLabel#FieldHint {{
        font-size: 11px;
    }}

    QLabel#PrivacyMark {{
        color: {SUCCESS};
        font-size: 10px;
        font-weight: 700;
        padding-top: 10px;
    }}

    QLabel#Attribution {{
        color: {TEXT_MUTED};
        font-size: 9px;
        padding-top: 7px;
    }}

    QLabel#LocalChip, QLabel#StatusChip, QLabel#InfoBadge, QLabel#MicroBadge {{
        background-color: {SURFACE_RAISED};
        color: {TEXT_SOFT};
        border: 1px solid {BORDER};
        border-radius: 9px;
        padding: 5px 9px;
        font-size: 10px;
        font-weight: 700;
    }}

    QLabel#LocalChip {{
        color: {SUCCESS};
        border-color: #28513c;
    }}

    QLabel#StatusChip[engineStatus="ready"] {{
        color: {SUCCESS};
        border-color: #28513c;
    }}

    QLabel#StatusChip[engineStatus="failed"] {{
        color: {ERROR};
        border-color: #65353a;
    }}

    QLabel#MicroBadge {{
        color: {TEXT_MUTED};
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 9px;
    }}

    QPushButton#NavButton {{
        background-color: transparent;
        color: {TEXT_SOFT};
        border: none;
        border-radius: 8px;
        text-align: left;
        padding: 9px 11px;
        min-height: 19px;
        font-size: 13px;
        font-weight: 500;
    }}

    QPushButton#NavButton:hover {{
        background-color: {SURFACE_RAISED};
        color: {TEXT};
    }}

    QPushButton#NavButton:checked {{
        background-color: {SURFACE_ACTIVE};
        color: {TEXT};
        border-left: 2px solid {ACCENT};
        font-weight: 700;
    }}

    QFrame#Card, QFrame#ControlBar, QFrame#RecordingCard {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    QFrame#TranscriptCard {{
        background-color: {SURFACE};
        border: 1px solid {BORDER_STRONG};
        border-radius: 12px;
    }}

    QFrame#VerticalDivider {{
        color: {BORDER};
        max-width: 1px;
    }}

    QLabel#StateDot {{
        color: {TEXT_MUTED};
        font-size: 10px;
    }}

    QLabel#StateLabel {{
        color: {TEXT_SOFT};
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1px;
    }}

    QFrame#RecordingCard[recordingState="ready"] QLabel#StateDot,
    QFrame#RecordingCard[recordingState="ready"] QLabel#StateLabel {{
        color: {SUCCESS};
    }}

    QFrame#RecordingCard[recordingState="listening"] {{
        border-color: #8f4950;
    }}

    QFrame#RecordingCard[recordingState="listening"] QLabel#StateDot,
    QFrame#RecordingCard[recordingState="listening"] QLabel#StateLabel {{
        color: {ERROR};
    }}

    QFrame#RecordingCard[recordingState="failed"] QLabel#StateDot,
    QFrame#RecordingCard[recordingState="failed"] QLabel#StateLabel {{
        color: {ERROR};
    }}

    QLabel#RecordTitle {{
        font-size: 17px;
        font-weight: 650;
    }}

    QLabel#MonoMuted {{
        color: {TEXT_MUTED};
        font-family: "Cascadia Mono", "Consolas", monospace;
        font-size: 11px;
    }}

    QLabel#ShortcutLine {{
        color: {TEXT_MUTED};
        font-family: "Cascadia Mono", "Consolas", monospace;
        font-size: 9px;
    }}

    QProgressBar#InputLevel {{
        background-color: {SURFACE_ACTIVE};
        border: none;
        border-radius: 3px;
        min-height: 6px;
        max-height: 6px;
    }}

    QProgressBar#InputLevel::chunk {{
        background-color: {SUCCESS};
        border-radius: 3px;
    }}

    QPushButton#RecordButton {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 9px;
        padding: 9px 14px;
        min-height: 18px;
        font-weight: 750;
    }}

    QPushButton#RecordButton:hover {{
        background-color: #ffffff;
    }}

    QPushButton#RecordButton:disabled {{
        background-color: {SURFACE_ACTIVE};
        color: {TEXT_MUTED};
    }}

    QPushButton#ModeButton {{
        background-color: {SURFACE_RAISED};
        color: {TEXT_SOFT};
        border: 1px solid {BORDER};
        border-radius: 7px;
        padding: 6px 11px;
        min-height: 18px;
    }}

    QPushButton#ModeButton:hover {{
        border-color: {BORDER_STRONG};
        color: {TEXT};
    }}

    QPushButton#ModeButton:checked {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border-color: {ACCENT};
        font-weight: 700;
    }}

    QPushButton#ActionButton, QPushButton#ActionPrimary {{
        background-color: {SURFACE_RAISED};
        color: {TEXT_SOFT};
        border: 1px solid {BORDER};
        border-radius: 7px;
        padding: 7px 11px;
        min-height: 18px;
    }}

    QPushButton#ActionButton:hover {{
        background-color: {SURFACE_ACTIVE};
        color: {TEXT};
        border-color: {BORDER_STRONG};
    }}

    QPushButton#ActionPrimary {{
        background-color: {ACCENT};
        color: {ACCENT_TEXT};
        border-color: {ACCENT};
        font-weight: 700;
    }}

    QPushButton#ActionButton:disabled, QPushButton#ActionPrimary:disabled {{
        background-color: {SURFACE_RAISED};
        color: #535c68;
        border-color: #222832;
    }}

    QComboBox#LanguageCombo {{
        background-color: {SURFACE_RAISED};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 7px;
        padding: 6px 10px;
        min-height: 22px;
    }}

    QComboBox#LanguageCombo:hover, QComboBox#LanguageCombo:focus {{
        border-color: {BORDER_STRONG};
    }}

    QComboBox#LanguageCombo::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {SURFACE_RAISED};
        color: {TEXT};
        border: 1px solid {BORDER_STRONG};
        border-radius: 7px;
        padding: 5px;
        selection-background-color: {SURFACE_ACTIVE};
        selection-color: {TEXT};
        outline: none;
    }}

    QPlainTextEdit#TranscriptEdit, QPlainTextEdit#NotesEditor {{
        background-color: #0d1014;
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 9px;
        padding: 14px;
        selection-background-color: {ACCENT};
        selection-color: {ACCENT_TEXT};
        font-family: "Nirmala UI", "Segoe UI Variable", "Segoe UI", sans-serif;
        font-size: 18px;
        line-height: 1.45;
    }}

    QPlainTextEdit#TranscriptEdit:focus, QPlainTextEdit#NotesEditor:focus {{
        border-color: {BORDER_STRONG};
    }}

    QLabel#TranscriptMetric {{
        color: {TEXT_MUTED};
        font-size: 10px;
    }}

    QLabel#StatValue {{
        color: {TEXT};
        font-size: 19px;
        font-weight: 700;
    }}

    QLabel#Microcopy {{
        color: {TEXT_MUTED};
        font-size: 9px;
    }}

    QLabel#HistoryItem {{
        background-color: {SURFACE_RAISED};
        color: {TEXT_SOFT};
        border: 1px solid #222832;
        border-radius: 7px;
        padding: 6px 8px;
        font-family: "Nirmala UI", "Segoe UI Variable", "Segoe UI", sans-serif;
        font-size: 10px;
    }}

    QSplitter#WorkspaceSplitter::handle {{
        background-color: {BG};
        width: 10px;
    }}

    QScrollArea#RailScroll, QScrollArea#RailScroll > QWidget > QWidget {{
        background-color: {BG};
        border: none;
    }}

    QScrollBar:vertical {{
        background-color: transparent;
        width: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background-color: #3a424d;
        border-radius: 4px;
        min-height: 28px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: #4a5562;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QStatusBar {{
        background-color: {SIDEBAR};
        color: {TEXT_MUTED};
        border-top: 1px solid {BORDER};
        font-size: 10px;
    }}
    """
