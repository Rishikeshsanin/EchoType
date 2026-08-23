from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget


def resample_levels(values: Iterable[float], count: int) -> list[float]:
    """Downsample level history into peak-preserving display buckets."""
    samples = [max(0.0, min(float(value), 1.0)) for value in values]
    if count <= 0:
        return []
    if not samples:
        return [0.0] * count
    if len(samples) <= count:
        return ([0.0] * (count - len(samples))) + samples

    output: list[float] = []
    for index in range(count):
        start = int(index * len(samples) / count)
        end = max(start + 1, int((index + 1) * len(samples) / count))
        output.append(max(samples[start:end]))
    return output


class AudioMeter(QWidget):
    """Lightweight animated bars fed by EchoType's existing audio telemetry."""

    BAR_COUNT = 34

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._levels = [0.0] * self.BAR_COUNT
        self._input_level = 0.0
        self._peak = 0.0
        self._active_color = QColor("#f7f8fa")
        self._quiet_color = QColor("#59616d")
        self._clip_color = QColor("#ffb24a")
        self.setObjectName("OverlayMeter")
        self.setMinimumHeight(27)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def sizeHint(self) -> QSize:
        return QSize(340, 27)

    def set_colors(self, active: str, quiet: str, clipping: str) -> None:
        self._active_color = QColor(active)
        self._quiet_color = QColor(quiet)
        self._clip_color = QColor(clipping)
        self.update()

    def set_levels(
        self,
        values: Iterable[float],
        *,
        level: float = 0.0,
        peak: float = 0.0,
    ) -> None:
        targets = resample_levels(values, self.BAR_COUNT)
        self._input_level = max(0.0, min(float(level) * 12.0, 1.0))
        if targets:
            targets[-1] = max(targets[-1], self._input_level)
        for index, target in enumerate(targets):
            current = self._levels[index]
            alpha = 0.72 if target > current else 0.28
            self._levels[index] = current + ((target - current) * alpha)
        self._peak = max(0.0, min(float(peak), 1.0))
        self.update()

    def reset(self) -> None:
        self._levels = [0.0] * self.BAR_COUNT
        self._input_level = 0.0
        self._peak = 0.0
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        gap = 3.0
        bar_width = max(2.0, (self.width() - gap * (self.BAR_COUNT - 1)) / self.BAR_COUNT)
        maximum_height = max(3.0, self.height() - 2.0)
        clipping = self._peak >= 0.985

        for index, value in enumerate(self._levels):
            height = max(2.0, value * maximum_height)
            x = index * (bar_width + gap)
            y = (self.height() - height) / 2.0
            if clipping and index >= self.BAR_COUNT - 4:
                color = self._clip_color
            else:
                color = self._active_color if value >= 0.16 else self._quiet_color
            painter.setBrush(color)
            painter.drawRoundedRect(
                QRectF(x, y, bar_width, height),
                bar_width / 2.0,
                bar_width / 2.0,
            )
