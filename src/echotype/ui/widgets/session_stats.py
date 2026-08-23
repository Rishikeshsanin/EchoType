from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget


def _duration(seconds: float) -> str:
    seconds = max(0, round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes}m {remainder:02d}s"


class _Stat(QWidget):
    def __init__(self, label: str, value: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.value = QLabel(value)
        self.value.setObjectName("StatValue")
        caption = QLabel(label)
        caption.setObjectName("StatLabel")
        layout.addWidget(self.value)
        layout.addWidget(caption)


class SessionStats(QFrame):
    """Small session scorecard updated from completed local utterances."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.words = 0
        self.utterances = 0
        self.saved_seconds = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 15)
        layout.setSpacing(11)
        title = QLabel("THIS SESSION")
        title.setObjectName("Eyebrow")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)
        self.words_stat = _Stat("words", "0")
        self.utterances_stat = _Stat("utterances", "0")
        self.rtf_stat = _Stat("last RTF", "—")
        self.saved_stat = _Stat("typing saved*", "0s")
        grid.addWidget(self.words_stat, 0, 0)
        grid.addWidget(self.utterances_stat, 0, 1)
        grid.addWidget(self.rtf_stat, 1, 0)
        grid.addWidget(self.saved_stat, 1, 1)
        layout.addLayout(grid)

        note = QLabel("*Estimate compared with 40 WPM typing")
        note.setObjectName("Microcopy")
        layout.addWidget(note)

    def add_utterance(self, metadata: dict[str, object]) -> None:
        self.words += int(metadata.get("words") or 0)
        self.utterances += 1
        self.saved_seconds += float(metadata.get("typing_seconds_saved") or 0.0)
        self.words_stat.value.setText(f"{self.words:,}")
        self.utterances_stat.value.setText(str(self.utterances))
        rtf = metadata.get("rtf")
        self.rtf_stat.value.setText(f"{float(rtf):.2f}" if isinstance(rtf, (int, float)) else "—")
        self.saved_stat.value.setText(_duration(self.saved_seconds))
