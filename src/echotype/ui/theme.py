"""Shared EchoType visual tokens and theme-aware Qt stylesheet."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

PALETTES = {
    "dark": {
        "bg": "#0b0d10",
        "surface": "#11151a",
        "raised": "#171c22",
        "border": "#252c35",
        "text": "#f5f7fa",
        "soft": "#b8c0cc",
        "muted": "#7d8795",
        "accent": "#e8edf5",
        "accent_text": "#0b0d10",
        "success": "#72d6a0",
        "danger": "#ff8f8f",
    },
    "light": {
        "bg": "#f3f5f7",
        "surface": "#ffffff",
        "raised": "#edf0f3",
        "border": "#d5dbe2",
        "text": "#15191f",
        "soft": "#424b57",
        "muted": "#6d7886",
        "accent": "#171b21",
        "accent_text": "#ffffff",
        "success": "#217a48",
        "danger": "#b42318",
    },
}


def resolved_theme(theme: str = "system") -> str:
    selected = str(theme or "system").lower()
    if selected in PALETTES:
        return selected
    app = QGuiApplication.instance()
    try:
        if app and app.styleHints().colorScheme() == Qt.ColorScheme.Light:
            return "light"
    except (AttributeError, RuntimeError):
        return "dark"
    return "dark"


def stylesheet(theme: str = "system") -> str:
    colors = PALETTES[resolved_theme(theme)]
    return f"""
    QWidget {{
        background: {colors["bg"]};
        color: {colors["text"]};
        font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
        font-size: 14px;
    }}

    QMainWindow {{ background: {colors["bg"]}; }}

    QFrame#Sidebar {{
        background: {colors["surface"]};
        border-right: 1px solid {colors["border"]};
    }}

    QLabel#Brand {{ font-size: 24px; font-weight: 700; }}
    QLabel#Tagline, QLabel#Muted {{ color: {colors["muted"]}; }}
    QLabel#PageTitle {{ font-size: 28px; font-weight: 700; }}
    QLabel#HeroTitle {{ font-size: 30px; font-weight: 700; }}
    QLabel#SectionTitle {{ color: {colors["soft"]}; font-size: 12px; font-weight: 700; }}
    QLabel#SettingsFeedback {{ color: {colors["success"]}; min-height: 18px; }}
    QLabel#SettingsFeedback[error="true"] {{ color: {colors["danger"]}; }}
    QLabel[error="true"] {{ color: {colors["danger"]}; }}

    QLabel#StatusChip {{
        background: {colors["raised"]};
        color: {colors["soft"]};
        border: 1px solid {colors["border"]};
        border-radius: 10px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
    }}

    QPushButton {{
        background: {colors["raised"]};
        color: {colors["soft"]};
        border: 1px solid {colors["border"]};
        border-radius: 9px;
        padding: 8px 12px;
    }}
    QPushButton:hover {{ color: {colors["text"]}; border-color: {colors["muted"]}; }}
    QPushButton:disabled {{ color: {colors["muted"]}; }}

    QPushButton#NavButton {{
        background: transparent;
        color: {colors["soft"]};
        border: none;
        border-radius: 10px;
        text-align: left;
        padding: 11px 14px;
        font-size: 14px;
        font-weight: 500;
    }}
    QPushButton#NavButton:hover {{ background: {colors["raised"]}; color: {colors["text"]}; }}
    QPushButton#NavButton:checked {{
        background: {colors["accent"]};
        color: {colors["accent_text"]};
        font-weight: 700;
    }}

    QFrame#Card, QFrame#SettingsCard {{
        background: {colors["surface"]};
        border: 1px solid {colors["border"]};
        border-radius: 16px;
    }}

    QPushButton#PrimaryButton {{
        background: {colors["accent"]};
        color: {colors["accent_text"]};
        border: none;
        border-radius: 10px;
        padding: 9px 15px;
        font-weight: 700;
    }}
    QPushButton#DangerButton {{ color: {colors["danger"]}; }}

    QPushButton#ModeButton {{
        background: {colors["raised"]};
        color: {colors["soft"]};
        border: 1px solid {colors["border"]};
        border-radius: 10px;
        padding: 8px 13px;
    }}
    QPushButton#ModeButton:checked {{
        background: {colors["accent"]};
        color: {colors["accent_text"]};
        font-weight: 700;
    }}

    QPlainTextEdit, QLineEdit, QComboBox, QTableWidget {{
        background: {colors["raised"]};
        color: {colors["text"]};
        border: 1px solid {colors["border"]};
        border-radius: 9px;
        padding: 8px;
        selection-background-color: {colors["accent"]};
        selection-color: {colors["accent_text"]};
    }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QHeaderView::section {{
        background: {colors["surface"]};
        color: {colors["soft"]};
        border: none;
        border-bottom: 1px solid {colors["border"]};
        padding: 9px;
        font-weight: 600;
    }}
    QTableWidget {{ gridline-color: {colors["border"]}; }}
    QProgressBar {{
        background: {colors["raised"]};
        color: {colors["soft"]};
        border: 1px solid {colors["border"]};
        border-radius: 7px;
        text-align: center;
        min-height: 20px;
    }}
    QProgressBar::chunk {{ background: {colors["success"]}; border-radius: 6px; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
    QStatusBar {{
        background: {colors["surface"]};
        color: {colors["muted"]};
        border-top: 1px solid {colors["border"]};
    }}
    """
