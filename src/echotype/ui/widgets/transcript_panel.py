from __future__ import annotations

from datetime import UTC, datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _button(text: str, *, primary: bool = False) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("ActionPrimary" if primary else "ActionButton")
    return button


class TranscriptPanel(QFrame):
    """Latest transcript, truthful language/script context, and actions."""

    copy_requested = Signal()
    paste_requested = Signal()
    notes_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TranscriptCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        self.eyebrow = QLabel("LATEST TRANSCRIPT")
        self.eyebrow.setObjectName("Eyebrow")
        title_stack.addWidget(self.eyebrow)
        self.title = QLabel("Ready for your next thought")
        self.title.setObjectName("PanelTitle")
        title_stack.addWidget(self.title)
        heading.addLayout(title_stack)
        heading.addStretch(1)
        self.language_badge = QLabel("NO TRANSCRIPT")
        self.language_badge.setObjectName("InfoBadge")
        heading.addWidget(self.language_badge)
        layout.addLayout(heading)

        self.transcript = QPlainTextEdit()
        self.transcript.setObjectName("TranscriptEdit")
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText("Your latest local transcript will appear here.")
        self.transcript.setMaximumBlockCount(1_000)
        layout.addWidget(self.transcript, 1)

        self.script_note = QLabel("Language and script details will appear after transcription.")
        self.script_note.setObjectName("FieldHint")
        self.script_note.setWordWrap(True)
        layout.addWidget(self.script_note)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(18)
        metrics.setVerticalSpacing(4)
        self.timing = QLabel("Audio — · Transcription —")
        self.speed = QLabel("Speed —")
        self.words = QLabel("0 words")
        self.signal = QLabel("SNR —")
        for label in (self.timing, self.speed, self.words, self.signal):
            label.setObjectName("TranscriptMetric")
        metrics.addWidget(self.timing, 0, 0)
        metrics.addWidget(self.speed, 0, 1)
        metrics.addWidget(self.words, 1, 0)
        metrics.addWidget(self.signal, 1, 1)
        metrics.setColumnStretch(2, 1)
        layout.addLayout(metrics)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.copy_button = _button("Copy", primary=True)
        self.paste_button = _button("Paste to last app")
        self.notes_button = _button("Send to Notes")
        self.clear_button = _button("Clear")
        self.copy_button.clicked.connect(self.copy_requested)
        self.paste_button.clicked.connect(self.paste_requested)
        self.notes_button.clicked.connect(self.notes_requested)
        self.clear_button.clicked.connect(self.clear_requested)
        for button in (self.copy_button, self.paste_button, self.notes_button, self.clear_button):
            button.setEnabled(False)
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

    @property
    def text(self) -> str:
        return self.transcript.toPlainText().strip()

    def set_transcript(self, text: str, metadata: dict[str, object]) -> None:
        self.set_processing(False)
        self.transcript.setPlainText(text)
        self.title.setText("Captured just now")
        has_text = bool(text.strip())
        for button in (self.copy_button, self.paste_button, self.notes_button, self.clear_button):
            button.setEnabled(has_text)

        script = str(metadata.get("script_label") or "Unknown")
        selected = str(metadata.get("language_name") or "")
        auto = str(metadata.get("language_code") or "auto") == "auto"
        if auto:
            self.language_badge.setText(f"{script.upper()} SCRIPT")
        else:
            self.language_badge.setText(f"{selected.upper()} SELECTED · {script.upper()} SCRIPT")
        self.script_note.setText(
            str(
                metadata.get("language_note")
                or "Script detected; language was not independently identified."
            )
        )

        audio = float(metadata.get("audio_seconds") or 0.0)
        elapsed = float(metadata.get("elapsed") or 0.0)
        self.timing.setText(f"Audio {audio:.1f}s · Transcription {elapsed:.1f}s")
        rtf = metadata.get("rtf")
        if isinstance(rtf, (int, float)) and rtf > 0:
            self.speed.setText(f"RTF {rtf:.2f} · {1.0 / rtf:.1f}× realtime")
        else:
            self.speed.setText("RTF —")
        count = int(metadata.get("words") or 0)
        self.words.setText(f"{count} word{'s' if count != 1 else ''}")
        snr = metadata.get("snr_db")
        signal = f"SNR {float(snr):.1f} dB" if isinstance(snr, (int, float)) else "SNR —"
        if metadata.get("denoised"):
            signal += " · Denoised"
        self.signal.setText(signal)

        timestamp = metadata.get("time")
        when = (
            datetime.fromtimestamp(float(timestamp), tz=UTC).astimezone()
            if isinstance(timestamp, (int, float))
            else datetime.now(tz=UTC).astimezone()
        )
        self.setToolTip(f"Completed {when:%d %b %Y, %I:%M:%S %p}")

    def set_processing(self, processing: bool) -> None:
        previous = bool(processing and self.text)
        self.setProperty("previousTranscript", previous)
        if previous:
            self.eyebrow.setText("PREVIOUS TRANSCRIPT")
            self.title.setText("Transcribing new audio…")
            self.script_note.setToolTip(
                "This language/script metadata belongs to the previous transcript."
            )
        else:
            self.eyebrow.setText("LATEST TRANSCRIPT")
            if self.text and self.title.text() == "Transcribing new audio…":
                self.title.setText("Captured previously")
            self.script_note.setToolTip("")
        self.style().unpolish(self)
        self.style().polish(self)

    def clear(self) -> None:
        self.set_processing(False)
        self.transcript.clear()
        self.title.setText("Ready for your next thought")
        self.language_badge.setText("NO TRANSCRIPT")
        self.script_note.setText("Language and script details will appear after transcription.")
        self.timing.setText("Audio — · Transcription —")
        self.speed.setText("Speed —")
        self.words.setText("0 words")
        self.signal.setText("SNR —")
        for button in (self.copy_button, self.paste_button, self.notes_button, self.clear_button):
            button.setEnabled(False)
