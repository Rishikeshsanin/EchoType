from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from echotype.core.languages import AUTO
from echotype.ui.widgets.audio_meter import AudioMeter
from echotype.ui.widgets.language_selector import LanguageSelector
from echotype.ui.widgets.session_stats import SessionStats
from echotype.ui.widgets.transcript_panel import TranscriptPanel


class RecordingPanel(QFrame):
    record_pressed = Signal()
    record_released = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RecordingCard")
        self.setMinimumHeight(286)
        self._engine_ready = False
        self._listening = False

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

        meter_heading = QHBoxLayout()
        input_label = QLabel("INPUT LEVEL")
        input_label.setObjectName("Eyebrow")
        meter_heading.addWidget(input_label)
        meter_heading.addStretch(1)
        self.input_state = QLabel("QUIET")
        self.input_state.setObjectName("InputState")
        meter_heading.addWidget(self.input_state)
        layout.addLayout(meter_heading)

        self.level = AudioMeter()
        self.level.setObjectName("InputMeter")
        self.level.setMinimumHeight(32)
        self.level.set_colors("#6dd6a0", "#4b5562", "#ff9f43")
        layout.addWidget(self.level)

        self.mic_state = QLabel("MIC ACTIVE · AMBIENT READY")
        self.mic_state.setObjectName("MicState")
        layout.addWidget(self.mic_state)

        self.record_button = QPushButton("Model loading…")
        self.record_button.setObjectName("RecordButton")
        self.record_button.setEnabled(False)
        self.record_button.pressed.connect(self.record_pressed)
        self.record_button.released.connect(self.record_released)
        layout.addWidget(self.record_button)

        shortcut_heading = QLabel("SHORTCUTS")
        shortcut_heading.setObjectName("Eyebrow")
        layout.addWidget(shortcut_heading)
        shortcut_grid = QGridLayout()
        shortcut_grid.setContentsMargins(0, 0, 0, 0)
        shortcut_grid.setHorizontalSpacing(8)
        shortcut_grid.setVerticalSpacing(5)
        self.shortcut_keycaps: dict[str, QLabel] = {}
        descriptions = (
            ("ptt", "Hold to talk"),
            ("toggle", "Toggle dictation"),
            ("paste", "Paste last transcript"),
            ("cancel", "Cancel recording"),
        )
        for row, (key, description) in enumerate(descriptions):
            keycap = QLabel("—")
            keycap.setObjectName("Keycap")
            keycap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            keycap.setMinimumWidth(76)
            keycap.setMaximumWidth(112)
            action = QLabel(description)
            action.setObjectName("ShortcutAction")
            shortcut_grid.addWidget(keycap, row, 0)
            shortcut_grid.addWidget(action, row, 1)
            self.shortcut_keycaps[key] = keycap
        shortcut_grid.setColumnStretch(1, 1)
        layout.addLayout(shortcut_grid)

    def set_shortcuts(self, ptt: str, toggle: str, paste: str, cancel: str) -> None:
        values = {"ptt": ptt, "toggle": toggle, "paste": paste, "cancel": cancel}
        for key, value in values.items():
            self.shortcut_keycaps[key].setText(str(value))

    def set_level(self, level: float, seconds: float) -> None:
        if self._listening:
            self.level.set_levels((float(level),), level=float(level), peak=float(level))
        elapsed = max(0, int(seconds if self._listening else 0.0))
        self.elapsed_label.setText(f"{elapsed // 60:02d}:{elapsed % 60:02d}")

    def set_audio_snapshot(self, snapshot: object) -> None:
        if not self._listening:
            return
        waveform = getattr(snapshot, "waveform", ())
        level = float(getattr(snapshot, "level", 0.0))
        peak = float(getattr(snapshot, "peak", 0.0))
        self.level.set_levels(waveform, level=level, peak=peak)
        if peak >= 0.985:
            self.input_state.setText("CLIPPING")
            self.input_state.setProperty("clipping", True)
        elif level >= 0.008:
            self.input_state.setText("VOICE")
            self.input_state.setProperty("clipping", False)
        else:
            self.input_state.setText("QUIET")
            self.input_state.setProperty("clipping", False)
        self.input_state.style().unpolish(self.input_state)
        self.input_state.style().polish(self.input_state)
        self.set_level(level, float(getattr(snapshot, "elapsed", 0.0)))

    def set_engine_status(self, status: str, detail: str) -> None:
        status = status.lower()
        self._engine_ready = status == "ready"
        self._listening = False
        self.level.reset()
        self.elapsed_label.setText("00:00")
        self.input_state.setText("QUIET")
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
        self._listening = state == "listening"
        if state == "listening":
            self.state_label.setText("LISTENING")
            self.title.setText("Listening — speak naturally")
            self.detail.setText(
                f"Text will return to {detail}." if detail else "Release to transcribe."
            )
            self.record_button.setText("Release to transcribe")
            self.record_button.setEnabled(True)
            self.mic_state.setText("MIC ACTIVE · CURRENT RECORDING")
        elif state == "processing":
            self.state_label.setText("PROCESSING")
            self.title.setText("Turning speech into text")
            self.detail.setText(detail)
            self.record_button.setText("Processing…")
            self.record_button.setEnabled(False)
            self.mic_state.setText("MIC ACTIVE · AMBIENT ONLY")
        elif state == "loading":
            self.state_label.setText("LOADING")
            self.detail.setText(detail)
            self.mic_state.setText("MIC STATUS · WAITING")
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
            self.mic_state.setText(
                "MIC ACTIVE · AMBIENT READY" if self._engine_ready else "MIC STATUS · WAITING"
            )
        if not self._listening:
            self.level.reset()
            self.elapsed_label.setText("00:00")
            self.input_state.setText("QUIET")
            self.input_state.setProperty("clipping", False)
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
            str(snapshot.get("hotkey_cancel") or "Esc"),
        )
        history = snapshot.get("history")
        self.history.set_entries(history if isinstance(history, list) else [])

    def set_engine_status(self, status: str, detail: str) -> None:
        self.recording.set_engine_status(status, detail)

    def set_recording_state(self, state: str, detail: str) -> None:
        self.recording.set_recording_state(state, detail)
        self.transcript_panel.set_processing(state.lower() == "processing")

    def set_audio_level(self, level: float, seconds: float) -> None:
        self.recording.set_level(level, seconds)

    def set_audio_snapshot(self, snapshot: object) -> None:
        self.recording.set_audio_snapshot(snapshot)

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
