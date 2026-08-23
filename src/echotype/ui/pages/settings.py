from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from echotype.core.audio import SAMPLE_RATE, AudioEngine
from echotype.core.languages import LANGUAGES, name_for_code, script_for_code, script_label
from echotype.services.hotkeys import KEY_ALIASES, label_for
from echotype.ui.theme import stylesheet


class SettingsPage(QWidget):
    """Categorized, persisted settings backed by the shared Settings service."""

    def __init__(
        self,
        settings,
        diagnostics,
        *,
        audio=None,
        engine=None,
        history=None,
        on_audio_changed: Callable[[], None] | None = None,
        on_hotkeys_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.diagnostics = diagnostics
        self.audio = audio
        self.engine = engine
        self.history = history
        self.on_audio_changed = on_audio_changed or (lambda: None)
        self.on_hotkeys_changed = on_hotkeys_changed or (lambda: None)
        self._loading_devices = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        intro = QLabel(
            "Preferences are stored locally for this Windows user and take effect immediately "
            "unless noted otherwise."
        )
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        self.feedback = QLabel("")
        self.feedback.setObjectName("SettingsFeedback")
        self.feedback.setWordWrap(True)
        outer.addWidget(self.feedback)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(0, 0, 12, 0)
        self.body_layout.setSpacing(14)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self._build_audio()
        self._build_language()
        self._build_dictation()
        self._build_shortcuts()
        self._build_compute()
        self._build_privacy()
        self._build_appearance()
        self._build_diagnostics()
        self.body_layout.addStretch(1)

        self.level_timer = QTimer(self)
        self.level_timer.timeout.connect(self._refresh_live_status)
        self.level_timer.start(150)
        self._refresh_live_status()

    def _section(self, title: str, description: str) -> QFormLayout:
        card = QFrame()
        card.setObjectName("SettingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 19, 22, 21)
        layout.setSpacing(10)
        heading = QLabel(title.upper())
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)
        copy = QLabel(description)
        copy.setObjectName("Muted")
        copy.setWordWrap(True)
        layout.addWidget(copy)
        form = QFormLayout()
        form.setContentsMargins(0, 8, 0, 0)
        form.setHorizontalSpacing(26)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addLayout(form)
        self.body_layout.addWidget(card)
        return form

    def _set(self, key: str, value, callback: Callable[[], None] | None = None) -> bool:
        try:
            self.settings.set(key, value)
            if callback:
                callback()
            self.feedback.setText("Saved locally")
            self.feedback.setProperty("error", False)
            self.feedback.style().unpolish(self.feedback)
            self.feedback.style().polish(self.feedback)
            return True
        except (OSError, TypeError, ValueError) as exc:
            self.feedback.setText(str(exc))
            self.feedback.setProperty("error", True)
            self.feedback.style().unpolish(self.feedback)
            self.feedback.style().polish(self.feedback)
            return False

    @staticmethod
    def _combo(options: list[tuple[str, object]], current) -> QComboBox:
        combo = QComboBox()
        for label, value in options:
            combo.addItem(label, value)
        index = combo.findData(current)
        combo.setCurrentIndex(max(index, 0))
        return combo

    def _checkbox(self, label: str, key: str) -> QCheckBox:
        control = QCheckBox(label)
        control.setChecked(bool(self.settings.get(key)))
        control.toggled.connect(lambda checked, name=key: self._set(name, checked))
        return control

    def _build_audio(self) -> None:
        form = self._section(
            "Audio",
            "Choose the capture source and tune the local enhancement stages supported by EchoType.",
        )
        device_row = QWidget()
        device_layout = QHBoxLayout(device_row)
        device_layout.setContentsMargins(0, 0, 0, 0)
        self.microphone = QComboBox()
        self.microphone.currentIndexChanged.connect(self._change_microphone)
        refresh = QPushButton("Refresh devices")
        refresh.clicked.connect(self._refresh_devices)
        device_layout.addWidget(self.microphone, 1)
        device_layout.addWidget(refresh)
        form.addRow("Microphone", device_row)

        self.input_info = QLabel()
        self.input_info.setObjectName("Muted")
        self.input_info.setWordWrap(True)
        form.addRow("Selected input", self.input_info)

        self.input_level = QProgressBar()
        self.input_level.setRange(0, 100)
        self.input_level.setFormat("Live input level  %p%")
        form.addRow("Input test", self.input_level)
        form.addRow("Noise reduction", self._checkbox("Reduce steady background noise", "denoise"))

        strength_row = QWidget()
        strength_layout = QHBoxLayout(strength_row)
        strength_layout.setContentsMargins(0, 0, 0, 0)
        strength = QSlider(Qt.Orientation.Horizontal)
        strength.setRange(0, 100)
        strength.setValue(round(float(self.settings.get("denoise_strength")) * 100))
        strength_value = QLabel(f"{strength.value()}%")
        strength.valueChanged.connect(lambda value: strength_value.setText(f"{value}%"))
        strength.sliderReleased.connect(
            lambda: self._set("denoise_strength", strength.value() / 100.0)
        )
        strength_layout.addWidget(strength, 1)
        strength_layout.addWidget(strength_value)
        form.addRow("Denoise strength", strength_row)
        form.addRow("Automatic gain", self._checkbox("Normalize quiet recordings", "auto_gain"))
        form.addRow("Low-frequency filter", self._checkbox("Remove sub-80 Hz rumble", "highpass"))
        form.addRow(
            "Speech trimming", self._checkbox("Trim leading and trailing silence", "vad_trim")
        )
        self._refresh_devices()

    def _refresh_devices(self) -> None:
        self._loading_devices = True
        current = self.settings.get("input_device")
        self.microphone.clear()
        self.microphone.addItem("System default input", None)
        for index, name in AudioEngine.list_devices():
            self.microphone.addItem(f"{name}  ·  Input {index}", index)
        selected = self.microphone.findData(current)
        self.microphone.setCurrentIndex(max(selected, 0))
        self._loading_devices = False
        self._update_input_info()

    def _change_microphone(self) -> None:
        if self._loading_devices:
            return
        if self._set("input_device", self.microphone.currentData(), self.on_audio_changed):
            self._update_input_info()

    def _update_input_info(self) -> None:
        selected = self.microphone.currentData()
        name = self.microphone.currentText() or "No input device detected"
        native = ""
        try:
            import sounddevice as sd

            info = (
                sd.query_devices(selected, "input")
                if selected is not None
                else sd.query_devices(kind="input")
            )
            native_rate = int(float(info.get("default_samplerate", 0) or 0))
            channels = int(info.get("max_input_channels", 0) or 0)
            native = f" Native: {native_rate} Hz, {channels} channel(s)."
        except Exception:  # noqa: BLE001 - PortAudio uses backend-specific exception types
            native = " Native format unavailable."
        self.input_info.setText(
            f"{name}. EchoType captures {SAMPLE_RATE:,} Hz mono float audio.{native}"
        )

    def _build_language(self) -> None:
        form = self._section(
            "Language",
            "A language selection constrains the writing script. Auto-detect uses script evidence and "
            "does not claim exact language identification for shared scripts.",
        )
        options = [(name, code) for code, name, _script, _primary in LANGUAGES]
        language = self._combo(options, self.settings.get("language"))
        self.language_note = QLabel()
        self.language_note.setObjectName("Muted")
        self.language_note.setWordWrap(True)

        def changed() -> None:
            code = str(language.currentData())
            self._set("language", code)
            script = script_for_code(code)
            if code == "auto":
                self.language_note.setText(
                    "Auto-detect preserves multilingual flexibility. Shared writing scripts are hints, not proof of a specific language."
                )
            else:
                self.language_note.setText(
                    f"{name_for_code(code)} constrains decoding to the {script_label(script)} writing script."
                )

        language.currentIndexChanged.connect(changed)
        form.addRow("Default language", language)
        form.addRow("How it works", self.language_note)
        changed()

    def _build_dictation(self) -> None:
        form = self._section(
            "Dictation",
            "Control the default text mode, deterministic local cleanup, punctuation, and delivery behavior.",
        )
        mode = self._combo(
            [("Verbatim", "verbatim"), ("Smart", "smart"), ("Notes", "notes")],
            self.settings.get("default_mode"),
        )
        mode.currentIndexChanged.connect(lambda: self._set("default_mode", mode.currentData()))
        form.addRow("Default mode", mode)
        form.addRow(
            "Smart cleanup", self._checkbox("Apply deterministic cleanup in Smart/Notes", "cleanup")
        )
        form.addRow(
            "Spoken punctuation",
            self._checkbox(
                "Convert “comma”, “new line”, and similar commands", "spoken_punctuation"
            ),
        )
        form.addRow(
            "Pause punctuation",
            self._checkbox("Use decoder word timing to infer pauses", "auto_punctuate"),
        )
        form.addRow(
            "Paste after dictation",
            self._checkbox("Restore the captured app and paste at its caret", "auto_paste"),
        )
        form.addRow(
            "Copy transcript",
            self._checkbox("Keep the delivered transcript on the clipboard", "auto_copy"),
        )

    def _build_shortcuts(self) -> None:
        form = self._section(
            "Shortcuts",
            "Global single-key shortcuts. EchoType prevents duplicate assignments before saving.",
        )
        choices = sorted(KEY_ALIASES, key=lambda name: label_for(name))
        self.shortcut_controls: dict[str, QComboBox] = {}
        fields = (
            ("Push-to-talk", "hotkey_ptt"),
            ("Toggle dictation", "hotkey_toggle"),
            ("Paste last", "hotkey_paste_last"),
            ("Cancel", "hotkey_cancel"),
        )
        for label, key in fields:
            combo = self._combo(
                [(label_for(name), name) for name in choices], self.settings.get(key)
            )
            combo.currentIndexChanged.connect(self._save_shortcuts)
            self.shortcut_controls[key] = combo
            form.addRow(label, combo)
        self.shortcut_feedback = QLabel("All shortcuts are valid and distinct.")
        self.shortcut_feedback.setObjectName("Muted")
        form.addRow("Status", self.shortcut_feedback)

    def _save_shortcuts(self) -> None:
        values = {key: combo.currentData() for key, combo in self.shortcut_controls.items()}
        assigned = list(values.values())
        if len(set(assigned)) != len(assigned):
            self.shortcut_feedback.setText("Conflict: each action must use a different shortcut.")
            self.shortcut_feedback.setProperty("error", True)
            return
        try:
            self.settings.update(values)
            self.on_hotkeys_changed()
            self.shortcut_feedback.setText(
                "Saved: " + " · ".join(label_for(value) for value in assigned)
            )
            self.shortcut_feedback.setProperty("error", False)
        except (OSError, TypeError, ValueError) as exc:
            self.shortcut_feedback.setText(str(exc))
            self.shortcut_feedback.setProperty("error", True)

    def _build_compute(self) -> None:
        form = self._section(
            "Compute",
            "Compute changes apply the next time the speech model loads. CPU always falls back to FP32.",
        )
        device = self._combo(
            [("Auto (recommended)", "auto"), ("CPU", "cpu"), ("NVIDIA CUDA", "cuda")],
            self.settings.get("device"),
        )
        device.currentIndexChanged.connect(lambda: self._set("device", device.currentData()))
        precision = self._combo(
            [("FP16 — faster CUDA", "fp16"), ("FP32 — widest compatibility", "fp32")],
            self.settings.get("precision"),
        )
        precision.currentIndexChanged.connect(
            lambda: self._set("precision", precision.currentData())
        )
        form.addRow("Preferred device", device)
        form.addRow("Precision", precision)
        diagnostic_snapshot = self.diagnostics.collect()
        self.detected_gpu = QLabel(str(diagnostic_snapshot.get("GPU", "Not detected")))
        self.runtime_device = QLabel()
        self.model_status = QLabel()
        self.model_revision = QLabel()
        self.model_cache = QLabel(str(diagnostic_snapshot.get("Model cache", "Unavailable")))
        self.model_revision.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        for label in (
            self.detected_gpu,
            self.runtime_device,
            self.model_status,
            self.model_revision,
            self.model_cache,
        ):
            label.setObjectName("Muted")
            label.setWordWrap(True)
        form.addRow("Detected GPU", self.detected_gpu)
        form.addRow("Current runtime", self.runtime_device)
        form.addRow("Model status", self.model_status)
        form.addRow("Model revision", self.model_revision)
        form.addRow("Model cache", self.model_cache)

    def _build_privacy(self) -> None:
        form = self._section(
            "Privacy",
            "Microphone processing and transcription run on this device after the model is available. "
            "EchoType never includes access tokens in diagnostics.",
        )
        form.addRow(
            "Transcript history",
            self._checkbox("Save completed transcripts locally", "history_enabled"),
        )
        form.addRow(
            "Private session",
            self._checkbox("Do not save transcripts while this is enabled", "private_session"),
        )
        retention = self._combo(
            [
                ("Keep until I clear it", 0),
                ("7 days", 7),
                ("30 days", 30),
                ("90 days", 90),
                ("1 year", 365),
            ],
            self.settings.get("history_retention_days"),
        )

        def retention_changed() -> None:
            days = int(retention.currentData())
            if self._set("history_retention_days", days) and self.history is not None:
                self.history.prune(days)

        retention.currentIndexChanged.connect(retention_changed)
        form.addRow("Retention", retention)
        clear = QPushButton("Clear local history…")
        clear.clicked.connect(self._clear_history)
        form.addRow("Delete stored data", clear)

    def _clear_history(self) -> None:
        if self.history is None:
            return
        answer = QMessageBox.question(
            self,
            "Clear local history?",
            "This permanently removes EchoType's saved transcript history from this device.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.feedback.setText("Local transcript history cleared")

    def _build_appearance(self) -> None:
        form = self._section(
            "Appearance",
            "Dark is the polished default. System and light palettes use the same extensible token architecture.",
        )
        theme = self._combo(
            [("Follow system", "system"), ("Dark", "dark"), ("Light", "light")],
            self.settings.get("theme"),
        )

        def change_theme() -> None:
            selected = str(theme.currentData())
            if self._set("theme", selected):
                app = QApplication.instance()
                if app is not None:
                    app.setStyleSheet(stylesheet(selected))

        theme.currentIndexChanged.connect(change_theme)
        form.addRow("Color theme", theme)

    def _build_diagnostics(self) -> None:
        form = self._section(
            "Diagnostics",
            "A sanitized snapshot for troubleshooting. Credentials and environment tokens are never included.",
        )
        self.diagnostics_report = QPlainTextEdit()
        self.diagnostics_report.setReadOnly(True)
        self.diagnostics_report.setMinimumHeight(245)
        form.addRow(self.diagnostics_report)
        actions = QWidget()
        row = QHBoxLayout(actions)
        row.setContentsMargins(0, 0, 0, 0)
        refresh = QPushButton("Refresh report")
        copy = QPushButton("Copy diagnostics")
        refresh.clicked.connect(self._refresh_diagnostics)
        copy.clicked.connect(self._copy_diagnostics)
        row.addWidget(refresh)
        row.addWidget(copy)
        row.addStretch(1)
        form.addRow(actions)
        self._refresh_diagnostics()

    def _refresh_diagnostics(self) -> None:
        self.diagnostics_report.setPlainText(self.diagnostics.report())

    def _copy_diagnostics(self) -> None:
        text = self.diagnostics.report()
        QGuiApplication.clipboard().setText(text)
        self.diagnostics_report.setPlainText(text)
        self.feedback.setText("Sanitized diagnostics copied")

    def _refresh_live_status(self) -> None:
        level = float(getattr(self.audio, "level", 0.0) or 0.0)
        self.input_level.setValue(max(0, min(100, round(level * 500))))
        engine = self.engine
        device = str(getattr(engine, "device", "not loaded")).upper()
        precision = str(getattr(engine, "precision", "")).upper()
        self.runtime_device.setText(f"{device} / {precision}" if precision else device)
        status = str(getattr(engine, "status", "not started"))
        detail = str(getattr(engine, "detail", "") or "")
        self.model_status.setText(f"{status.upper()} — {detail}" if detail else status.upper())
        revision = (
            getattr(engine, "model_revision", None)
            or self.settings.get("model_revision")
            or "Not resolved yet"
        )
        repo = getattr(engine, "model_repo", "") or "SharadhNaiduTrains/sravaani-flow-model"
        self.model_revision.setText(f"{repo} @ {revision}")
