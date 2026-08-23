from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Slot
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPaintEvent, QPalette
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from echotype.ui.widgets.audio_meter import AudioMeter

HIDDEN = "hidden"
LISTENING = "listening"
PROCESSING = "processing"
SUCCESS = "success"
CANCELLED = "cancelled"
ERROR = "error"
OVERLAY_STATES = frozenset({HIDDEN, LISTENING, PROCESSING, SUCCESS, CANCELLED, ERROR})

_PROCESS_NAMES = {
    "notepad": "Notepad",
    "chrome": "Google Chrome",
    "msedge": "Microsoft Edge",
    "firefox": "Mozilla Firefox",
    "code": "Visual Studio Code",
    "devenv": "Visual Studio",
    "winword": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpnt": "Microsoft PowerPoint",
    "outlook": "Microsoft Outlook",
    "teams": "Microsoft Teams",
    "slack": "Slack",
    "discord": "Discord",
    "wt": "Windows Terminal",
    "windowsterminal": "Windows Terminal",
    "powershell": "Windows PowerShell",
    "pycharm64": "PyCharm",
    "chatgpt": "ChatGPT",
    "cursor": "Cursor",
}

_TITLE_PRODUCTS = (
    ("visual studio code", "Visual Studio Code"),
    ("google chrome", "Google Chrome"),
    ("mozilla firefox", "Mozilla Firefox"),
    ("microsoft edge", "Microsoft Edge"),
    ("microsoft word", "Microsoft Word"),
    ("microsoft excel", "Microsoft Excel"),
    ("microsoft powerpoint", "Microsoft PowerPoint"),
    ("windows terminal", "Windows Terminal"),
    ("notepad", "Notepad"),
)


def format_elapsed(seconds: float, *, suffix: bool = False) -> str:
    """Format compact overlay time, retaining tenths through long recordings."""
    value = max(0.0, float(seconds))
    if value < 60.0:
        text = f"{value:04.1f}" if not suffix else f"{value:.1f}"
    else:
        minutes = int(value // 60)
        text = f"{minutes}:{value - minutes * 60:04.1f}"
    return f"{text}s" if suffix else text


def target_display_name(title: str = "", process_name: str = "") -> str:
    """Turn window/process metadata into a short, human-readable app name."""
    process = Path(str(process_name or "")).stem.lower().strip()
    if process in _PROCESS_NAMES:
        return _PROCESS_NAMES[process]

    clean_title = re.sub(r"\s+", " ", str(title or "")).strip()
    lowered = clean_title.casefold()
    for needle, product in _TITLE_PRODUCTS:
        if needle in lowered:
            return product

    if process and process not in {"applicationframehost", "explorer"}:
        readable = re.sub(r"[-_]+", " ", process).strip().title()
        if readable:
            return readable[:48]

    parts = [part.strip() for part in re.split(r"\s[-—]\s", clean_title) if part.strip()]
    candidate = parts[-1] if len(parts) > 1 else clean_title
    return (candidate or "Active application")[:48]


class RecordingOverlay(QWidget):
    """Frameless no-focus system overlay for dictation lifecycle feedback."""

    WIDTH = 388
    HEIGHT = 116

    def __init__(
        self,
        audio_source: object,
        parent: QWidget | None = None,
        *,
        bottom_margin: int = 72,
    ) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if hasattr(Qt.WindowType, "WindowTransparentForInput"):
            flags |= Qt.WindowType.WindowTransparentForInput
        super().__init__(parent, flags)
        self.audio_source = audio_source
        self.bottom_margin = max(12, int(bottom_margin))
        self.current_state = HIDDEN
        self._payload: dict[str, Any] = {}
        self._state_started = time.monotonic()

        self.setObjectName("RecordingOverlay")
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 14, 18, 13)
        outer.setSpacing(5)

        header = QHBoxLayout()
        header.setSpacing(7)
        self.indicator = QLabel("●")
        self.indicator.setObjectName("OverlayIndicator")
        self.indicator.setFixedWidth(12)
        header.addWidget(self.indicator)

        self.state_label = QLabel("LISTENING")
        self.state_label.setObjectName("OverlayState")
        header.addWidget(self.state_label)
        header.addStretch(1)

        self.timer_label = QLabel("00.0")
        self.timer_label.setObjectName("OverlayTimer")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self.timer_label)
        outer.addLayout(header)

        self.meter = AudioMeter(self)
        outer.addWidget(self.meter)

        self.detail_label = QLabel("Processing locally")
        self.detail_label.setObjectName("OverlayDetail")
        self.detail_label.setFixedHeight(27)
        self.detail_label.hide()
        outer.addWidget(self.detail_label)

        self.target_label = QLabel("Active application")
        self.target_label.setObjectName("OverlayTarget")
        outer.addWidget(self.target_label)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(33)
        self._tick_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._tick_timer.timeout.connect(self._tick)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._hide_now)
        self._apply_theme()

    @Slot(str, object)
    def set_state(self, state: str, payload: object = None) -> None:
        normalized = str(state or HIDDEN).strip().lower()
        if normalized == "transcribing":
            normalized = PROCESSING
        if normalized not in OVERLAY_STATES:
            normalized = ERROR
            payload = {"detail": f"Unknown overlay state: {state}"}

        self._dismiss_timer.stop()
        self.current_state = normalized
        self._payload = dict(payload) if isinstance(payload, dict) else {}
        self._state_started = time.monotonic()

        if normalized == HIDDEN:
            self._hide_now()
            return

        target = target_display_name(
            str(self._payload.get("target_title", "")),
            str(self._payload.get("target_process", "")),
        )
        if target != "Active application" or not self.target_label.text():
            self.target_label.setText(target)

        presentations = {
            LISTENING: ("●", "LISTENING", ""),
            PROCESSING: ("◌", "TRANSCRIBING", "Processing locally"),
            SUCCESS: ("●", "DONE", "Transcript delivered"),
            CANCELLED: ("–", "CANCELLED", "Recording cancelled"),
            ERROR: ("!", "ERROR", "Something went wrong"),
        }
        glyph, label, default_detail = presentations[normalized]
        self.indicator.setText(glyph)
        self.state_label.setText(label)
        detail = str(self._payload.get("detail", "") or default_detail)
        self.detail_label.setText(detail)

        listening = normalized == LISTENING
        self.meter.setVisible(listening)
        self.detail_label.setVisible(not listening)
        self.timer_label.setVisible(normalized in {LISTENING, PROCESSING})
        if not listening:
            self.meter.reset()

        self._apply_theme()
        self._position_for_target(self._payload.get("target_hwnd"))
        self.show()
        self._apply_native_no_activate()
        if normalized in {LISTENING, PROCESSING}:
            self._tick_timer.start()
        else:
            self._tick_timer.stop()
        self._tick()

        dismiss_ms = self._payload.get("dismiss_ms")
        if normalized in {SUCCESS, CANCELLED, ERROR}:
            if not isinstance(dismiss_ms, int):
                dismiss_ms = 750 if normalized != ERROR else 1_200
            self._dismiss_timer.start(max(100, dismiss_ms))

    def _hide_now(self) -> None:
        self._tick_timer.stop()
        self.current_state = HIDDEN
        self.hide()

    def _tick(self) -> None:
        if self.current_state == LISTENING:
            try:
                snapshot = self.audio_source.snapshot()
                self.timer_label.setText(format_elapsed(snapshot.elapsed))
                self.meter.set_levels(
                    snapshot.waveform,
                    level=snapshot.level,
                    peak=snapshot.peak,
                )
            except Exception:  # noqa: BLE001 - telemetry must never disrupt capture
                self.timer_label.setText(format_elapsed(time.monotonic() - self._state_started))
        elif self.current_state == PROCESSING:
            self.timer_label.setText(
                format_elapsed(time.monotonic() - self._state_started, suffix=True)
            )

    def _position_for_target(self, hwnd: object) -> None:
        point: QPoint | None = None
        if sys.platform == "win32" and hwnd:
            try:
                import win32gui

                left, top, right, bottom = win32gui.GetWindowRect(int(hwnd))
                point = QPoint((left + right) // 2, (top + bottom) // 2)
            except Exception:  # noqa: BLE001 - optional Windows placement enhancement
                point = None

        screen = QGuiApplication.screenAt(point) if point is not None else None
        if screen is None:
            screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        x = available.x() + ((available.width() - self.width()) // 2)
        y = available.bottom() - self.height() - self.bottom_margin + 1
        x = min(max(x, available.left()), available.right() - self.width() + 1)
        y = min(max(y, available.top()), available.bottom() - self.height() + 1)
        self.move(x, y)

    def _apply_native_no_activate(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import win32con
            import win32gui

            hwnd = int(self.winId())
            extended = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            extended |= (
                win32con.WS_EX_NOACTIVATE
                | win32con.WS_EX_TOOLWINDOW
                | win32con.WS_EX_TRANSPARENT
            )
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, extended)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
        except Exception:  # noqa: BLE001 - Qt flags remain a safe fallback
            return

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        palette = app.palette() if app is not None else QPalette()
        dark = palette.color(QPalette.ColorRole.Window).lightness() < 128
        if dark:
            self._colors = {
                "background": "#15191f",
                "border": "#323945",
                "text": "#f7f8fa",
                "muted": "#9ba5b2",
                "quiet": "#4c5664",
                "listening": "#ff5d69",
                "processing": "#77a7ff",
                "success": "#72d6a0",
                "cancelled": "#aab2bd",
                "error": "#ff8a73",
                "clip": "#ffb24a",
            }
        else:
            self._colors = {
                "background": "#fbfcfe",
                "border": "#d8dee8",
                "text": "#171b22",
                "muted": "#667080",
                "quiet": "#c3cad5",
                "listening": "#d93648",
                "processing": "#356fd2",
                "success": "#218653",
                "cancelled": "#657080",
                "error": "#c84332",
                "clip": "#c97809",
            }

        accent = self._colors.get(self.current_state, self._colors["processing"])
        self.setStyleSheet(
            f"""
            QWidget#RecordingOverlay, QWidget#OverlayMeter {{ background: transparent; }}
            QLabel {{ background: transparent; color: {self._colors['text']}; }}
            QLabel#OverlayIndicator {{ color: {accent}; font-size: 13px; }}
            QLabel#OverlayState {{ font-size: 12px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#OverlayTimer {{
                color: {self._colors['muted']};
                font-family: Consolas, monospace;
                font-size: 12px;
            }}
            QLabel#OverlayDetail {{ color: {self._colors['muted']}; font-size: 12px; }}
            QLabel#OverlayTarget {{ color: {self._colors['muted']}; font-size: 11px; }}
            """
        )
        self.meter.set_colors(self._colors["text"], self._colors["quiet"], self._colors["clip"])
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QColor(self._colors["border"]))
        painter.setBrush(QColor(self._colors["background"]))
        painter.drawRoundedRect(rect, 14.0, 14.0)
