"""Shared EchoType visual tokens and Qt stylesheet."""

BG = "#0b0d10"
SURFACE = "#11151a"
SURFACE_RAISED = "#171c22"
BORDER = "#252c35"
TEXT = "#f5f7fa"
TEXT_SOFT = "#b8c0cc"
TEXT_MUTED = "#7d8795"
ACCENT = "#e8edf5"
ACCENT_TEXT = "#0b0d10"
SUCCESS = "#72d6a0"


def stylesheet() -> str:
    return f"""
    QWidget {{
        background: {BG};
        color: {TEXT};
        font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
        font-size: 14px;
    }}

    QMainWindow {{
        background: {BG};
    }}

    QFrame#Sidebar {{
        background: {SURFACE};
        border-right: 1px solid {BORDER};
    }}

    QLabel#Brand {{
        font-size: 24px;
        font-weight: 700;
    }}

    QLabel#Tagline, QLabel#Muted {{
        color: {TEXT_MUTED};
    }}

    QLabel#PageTitle {{
        font-size: 28px;
        font-weight: 700;
    }}

    QLabel#HeroTitle {{
        font-size: 30px;
        font-weight: 700;
    }}

    QLabel#StatusChip {{
        background: {SURFACE_RAISED};
        color: {TEXT_SOFT};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
    }}

    QPushButton#NavButton {{
        background: transparent;
        color: {TEXT_SOFT};
        border: none;
        border-radius: 10px;
        text-align: left;
        padding: 11px 14px;
        font-size: 14px;
        font-weight: 500;
    }}

    QPushButton#NavButton:hover {{
        background: {SURFACE_RAISED};
        color: {TEXT};
    }}

    QPushButton#NavButton:checked {{
        background: {ACCENT};
        color: {ACCENT_TEXT};
        font-weight: 700;
    }}

    QFrame#Card {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 18px;
    }}

    QPushButton#PrimaryButton {{
        background: {ACCENT};
        color: {ACCENT_TEXT};
        border: none;
        border-radius: 12px;
        padding: 11px 18px;
        font-weight: 700;
    }}

    QPushButton#PrimaryButton:hover {{
        background: #ffffff;
    }}

    QPushButton#ModeButton {{
        background: {SURFACE_RAISED};
        color: {TEXT_SOFT};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 8px 13px;
    }}

    QPushButton#ModeButton:checked {{
        background: {ACCENT};
        color: {ACCENT_TEXT};
        font-weight: 700;
    }}

    QPlainTextEdit, QLineEdit {{
        background: {SURFACE_RAISED};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 10px;
        selection-background-color: {ACCENT};
        selection-color: {ACCENT_TEXT};
    }}

    QStatusBar {{
        background: {SURFACE};
        color: {TEXT_MUTED};
        border-top: 1px solid {BORDER};
    }}
    """
