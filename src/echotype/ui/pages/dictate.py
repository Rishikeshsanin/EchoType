from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from echotype.core.languages import AUTO
from echotype.ui.widgets.language_selector import LanguageSelector
from echotype.ui.widgets.session_stats import SessionStats
from echotype.ui.widgets.transcript_panel import TranscriptPanel


class RecordingPanel(QFrame):
    record_pressed = Signal()
    record_released = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecordingCard")
        self.setMinimumHeight(190)
        self._engine_ready = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 15, 16, 15)
        layout.setSpacing(9)

        state_row = QHBoxLayout()
        self.state_dot = QLabel("●")
        self.state_dot.setObjectName("StateDot")
        self.state_label = QLabel("STARTING")
        self.state_label.setObjectName("StateLabel")
        state_row.addWidget(self.state_dot)
        state_row.addWidget(self.state_label)
        state_row.addStretch(1)
        self.elapsed_label = QLabel("00:00")
        self.elapsed_label.setObjectName("MonoMuted")
        state_row.addWidget(self.elapsed_label)
        layout.addLayout(state_row)

        self.title = QLabel("Loading the local speech engine")
        self.title.setObjectName("RecordTitle")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)

        self.detail = QLabel("Normal dictation stays on this device.")
        self.detail.setObjectName("FieldHint")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)

        level_row = QHBoxLayout()
        input_label = QLabel("INPUT")
        input_label.setObjectName("Eyebrow")
        level_row.addWidget(input_label)
        self.level = QProgressBar()
        self.level.setObjectName("InputLevel")
        self.level.setRange(0, 1000)
        self.level.setValue(0)
        self.level.setTextVisible(False)
        level_row.addWidget(self.level, 1)
        layout.addLayout(level_row)

        self.record_button = QPushButton("Model loading…")
        self.record_button.setObjectName("RecordButton")
        self.record_button.setEnabled(False)
        self.record_button.pressed.connect(self.record_pressed)
        self.record_button.released.connect(self.record_released)
        layout.addWidget(self.record_button)

        self.shortcuts = QLabel(
            "RIGHT SHIFT  Hold to talk   ·   F9  Toggle   ·   F11  Repaste   ·   ESC  Cancel"
        )
        self.shortcuts.setObjectName("ShortcutLine")
        self.shortcuts.setWordWrap(True)
        layout.addWidget(self.shortcuts)

    def set_shortcuts(self, ptt: str, toggle: str, paste: str) -> None:
        self.shortcuts.setText(
            f"{ptt.upper()}  Hold to talk   ·   {toggle.upper()}  Toggle   ·   "
            f"{paste.upper()}  Repaste   ·   ESC  Cancel"
        )

    def set_level(self, level: float, seconds: float) -> None:
        self.level.setValue(max(0, min(1000, int(float(level) * 15_000))))
        elapsed = max(0, int(seconds))
        self.elapsed_label.setText(f"{elapsed // 60:02d}:{elapsed % 60:02d}")

    def set_engine_status(self, status: str, detail: str) -> None:
        status = status.lower()
        self._engine_ready = status == "ready"
        if status == "loading":
            self.state_label.setText("LOADING")
            self.title.setText("Loading the local speech engine")
            self.detail.setText(detail or "Preparing SraVaani on this device.")
            self.record_button.setText("Model loading…")
        elif status == "failed":
            self.state_label.setText("ERROR")
            self.title.setText("Speech engine unavailable")
            self.detail.setText(detail or "Check the model setup and try again.")
            self.record_button.setText("Unavailable")
        elif status == "busy":
            self.state_label.setText("PROCESSING")
            self.title.setText("Turning speech into text")
            self.detail.setText(detail)
            self.record_button.setText("Processing…")
        elif status == "ready":
            self.state_label.setText("READY")
            self.title.setText("Hold Right Shift and speak")
            self.detail.setText("Release the key to transcribe and return text to your last app.")
            self.record_button.setText("Hold to speak")
        self.setProperty("recordingState", status)
        self.style().unpolish(self)
        self.style().polish(self)
        self.record_button.setEnabled(self._engine_ready)

    def set_recording_state(self, state: str, detail: str) -> None:
        state = state.lower()
        if state == "listening":
            self.state_label.setText("LISTENING")
            self.title.setText("Listening — speak naturally")
            self.detail.setText(
                f"Text will return to {detail}." if detail else "Release to transcribe."
            )
            self.record_button.setText("Release to transcribe")
            self.record_button.setEnabled(True)
        elif state == "processing":
            self.state_label.setText("PROCESSING")
            self.title.setText("Turning speech into text")
            self.detail.setText(detail)
            self.record_button.setText("Processing…")
            self.record_button.setEnabled(False)
        elif state == "loading":
            self.state_label.setText("LOADING")
            self.detail.setText(detail)
        else:
            self.state_label.setText("READY" if self._engine_ready else "STARTING")
            self.title.setText(
                "Hold Right Shift and speak"
                if self._engine_ready
                else "Loading the local speech engine"
            )
            self.detail.setText(detail or "Normal dictation stays on this device.")
            self.record_button.setEnabled(self._engine_ready)
            self.record_button.setText("Hold to speak" if self._engine_ready else "Model loading…")
        self.setProperty("recordingState", state)
        self.style().unpolish(self)
        self.style().polish(self)


class HistoryPreview(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(145)
        self._entries: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        row = QHBoxLayout()
        title = QLabel("RECENT HISTORY")
        title.setObjectName("Eyebrow")
        row.addWidget(title)
        row.addStretch(1)
        self.count = QLabel("LOCAL")
        self.count.setObjectName("MicroBadge")
        row.addWidget(self.count)
        layout.addLayout(row)

        self.items: list[QLabel] = []
        for _ in range(3):
            label = QLabel("—")
            label.setObjectName("HistoryItem")
            label.setWordWrap(True)
            label.setMaximumHeight(42)
            self.items.append(label)
            layout.addWidget(label)

    def set_entries(self, entries: list[dict]) -> None:
        self._entries = [dict(entry) for entry in entries if entry.get("text")][:3]
        self._render()

    def prepend(self, text: str, metadata: dict[str, object]) -> None:
        self._entries.insert(0, {"text": text, **metadata})
        self._entries = self._entries[:3]
        self._render()

    def _render(self) -> None:
        for index, label in enumerate(self.items):
            if index >= len(self._entries):
                label.setText("No local transcript yet" if index == 0 else "")
                label.setVisible(index == 0)
                continue
            entry = self._entries[index]
            text = " ".join(str(entry.get("text", "")).split())
            if len(text) > 72:
                text = text[:69].rstrip() + "…"
            timestamp = entry.get("time")
            if isinstance(timestamp, (int, float)):
                stamp = (
                    datetime.fromtimestamp(float(timestamp), tz=UTC).astimezone().strftime("%H:%M")
                )
                text = f"{stamp}  {text}"
            label.setText(text)
            label.setToolTip(str(entry.get("text", "")))
            label.setVisible(True)


class DictatePage(QWidget):
    mode_changed = Signal(str)
    language_changed = Signal(str)
    record_pressed = Signal()
    record_released = Signal()
    paste_requested = Signal()
    clear_requested = Signal()
    notes_requested = Signal(str)
    notification = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DictatePage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        controls = QFrame()
        controls.setObjectName("ControlBar")
        control_layout = QHBoxLayout(controls)
        control_layout.setContentsMargins(16, 13, 16, 13)
        control_layout.setSpacing(18)

        self.language_selector = LanguageSelector()
        self.language_selector.language_changed.connect(self.language_changed)
        control_layout.addWidget(self.language_selector, 1)

        divider = QFrame()
        divider.setObjectName("VerticalDivider")
        divider.setFrameShape(QFrame.Shape.VLine)
        control_layout.addWidget(divider)

        mode_stack = QVBoxLayout()
        mode_stack.setSpacing(5)
        mode_label = QLabel("OUTPUT MODE")
        mode_label.setObjectName("Eyebrow")
        mode_stack.addWidget(mode_label)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(5)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_buttons: dict[str, QPushButton] = {}
        descriptions = {
            "verbatim": "Keep wording with minimal cleanup",
            "smart": "Local punctuation and safe cleanup",
            "notes": "Notes output path; advanced structuring is still in development",
        }
        for name in ("Verbatim", "Smart", "Notes"):
            key = name.lower()
            button = QPushButton(name)
            button.setObjectName("ModeButton")
            button.setCheckable(True)
            button.setChecked(key == "smart")
            button.setToolTip(descriptions[key])
            button.clicked.connect(lambda checked=False, mode=key: self.mode_changed.emit(mode))
            self.mode_group.addButton(button)
            self.mode_buttons[key] = button
            mode_row.addWidget(button)
        mode_stack.addLayout(mode_row)
        mode_hint = QLabel("Processing is deterministic and local")
        mode_hint.setObjectName("FieldHint")
        mode_stack.addWidget(mode_hint)
        control_layout.addLayout(mode_stack)
        layout.addWidget(controls)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("WorkspaceSplitter")
        splitter.setChildrenCollapsible(False)
        self.transcript_panel = TranscriptPanel()
        self.transcript_panel.copy_requested.connect(self._copy_transcript)
        self.transcript_panel.paste_requested.connect(self.paste_requested)
        self.transcript_panel.notes_requested.connect(self._send_to_notes)
        self.transcript_panel.clear_requested.connect(self._clear_transcript)
        splitter.addWidget(self.transcript_panel)

        rail = QWidget()
        rail.setObjectName("RightRail")
        rail.setMinimumWidth(286)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(0, 0, 0, 0)
        rail_layout.setSpacing(10)
        self.recording = RecordingPanel()
        self.recording.record_pressed.connect(self.record_pressed)
        self.recording.record_released.connect(self.record_released)
        rail_layout.addWidget(self.recording)
        self.session_stats = SessionStats()
        rail_layout.addWidget(self.session_stats)
        self.history = HistoryPreview()
        self.history.setMinimumHeight(145)
        rail_layout.addWidget(self.history, 1)

        rail_scroll = QScrollArea()
        rail_scroll.setObjectName("RailScroll")
        rail_scroll.setWidgetResizable(True)
        rail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        rail_scroll.setMinimumWidth(286)
        rail_scroll.setMaximumWidth(370)
        rail_scroll.setWidget(rail)
        splitter.addWidget(rail_scroll)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([680, 320])
        layout.addWidget(splitter, 1)

    def apply_snapshot(self, snapshot: dict[str, object]) -> None:
        self.language_selector.set_language(str(snapshot.get("language") or AUTO))
        mode = str(snapshot.get("mode") or "smart")
        if mode in self.mode_buttons:
            self.mode_buttons[mode].setChecked(True)
        self.recording.set_shortcuts(
            str(snapshot.get("hotkey_ptt") or "Right Shift"),
            str(snapshot.get("hotkey_toggle") or "F9"),
            str(snapshot.get("hotkey_paste_last") or "F11"),
        )
        history = snapshot.get("history")
        self.history.set_entries(history if isinstance(history, list) else [])

    def set_engine_status(self, status: str, detail: str) -> None:
        self.recording.set_engine_status(status, detail)

    def set_recording_state(self, state: str, detail: str) -> None:
        self.recording.set_recording_state(state, detail)

    def set_audio_level(self, level: float, seconds: float) -> None:
        self.recording.set_level(level, seconds)

    def show_transcript(self, text: str, metadata: object) -> None:
        data = dict(metadata) if isinstance(metadata, dict) else {}
        self.transcript_panel.set_transcript(text, data)
        self.session_stats.add_utterance(data)
        self.history.prepend(text, data)

    def _copy_transcript(self) -> None:
        text = self.transcript_panel.text
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.notification.emit("Transcript copied to clipboard")

    def _send_to_notes(self) -> None:
        text = self.transcript_panel.text
        if text:
            self.notes_requested.emit(text)

    def _clear_transcript(self) -> None:
        self.transcript_panel.clear()
        self.clear_requested.emit()
        self.notification.emit("Current transcript cleared; local history was kept")
