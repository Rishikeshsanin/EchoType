from __future__ import annotations

import os
import threading
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from echotype.app import runtime as runtime_module  # noqa: E402
from echotype.core.transcription import Job, Result  # noqa: E402
from echotype.services.history import HistoryStore  # noqa: E402
from echotype.services.settings import Settings  # noqa: E402
from echotype.services.vocabulary import VocabularyService  # noqa: E402


@pytest.fixture(scope="session")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("title", "process_name"),
    (
        ("Untitled - Notepad", "notepad.exe"),
        ("EchoType test - Google Chrome", "chrome.exe"),
        ("test.py - EchoType - Visual Studio Code", "Code.exe"),
    ),
)
def test_original_external_target_survives_overlay_and_reaches_delivery(
    qt_app: QApplication,
    tmp_path,
    monkeypatch,
    title: str,
    process_name: str,
) -> None:
    """Lock the proven V2 invariant: capture once, submit once, deliver the same object."""
    del qt_app
    settings = Settings(tmp_path / "settings.json")
    settings.update(
        {
            "auto_copy": True,
            "auto_paste": True,
            "history_enabled": False,
            "min_record_seconds": 0.1,
        }
    )
    history = HistoryStore(tmp_path / "history.jsonl", settings=settings)
    vocabulary = VocabularyService(tmp_path / "vocabulary.json")
    monkeypatch.setattr(runtime_module, "Settings", lambda: settings)
    monkeypatch.setattr(runtime_module, "HistoryStore", lambda settings=None: history)
    monkeypatch.setattr(runtime_module, "VocabularyService", lambda legacy_terms=None: vocabulary)

    target = SimpleNamespace(
        hwnd=41,
        title=title,
        process_name=process_name,
        valid=True,
        sensitive=False,
    )
    capture_calls: list[object] = []

    def capture_once():
        capture_calls.append(target)
        return target

    monkeypatch.setattr(runtime_module, "capture_focus", capture_once)
    runtime = runtime_module.DictationRuntime()
    runtime.set_own_hwnds({99, 100})
    runtime.engine.status = runtime_module.READY
    runtime.engine.model = object()
    runtime.audio._stream = SimpleNamespace(active=True)
    runtime.audio.begin = lambda: None
    runtime.audio.end = lambda: np.ones(16_000, dtype=np.float32)
    runtime.audio.process = lambda audio: (
        audio,
        {"seconds": 1.0, "speech_ratio": 1.0},
    )

    overlays: list[tuple[str, dict[str, object]]] = []
    runtime.overlay_state.connect(lambda state, payload: overlays.append((state, dict(payload))))
    submitted = threading.Event()
    submission: dict[str, object] = {}

    def submit(_audio, _info, **kwargs):
        submission.update(kwargs)
        submitted.set()

    runtime.engine.submit = submit

    runtime.begin_recording()
    # EchoType and its overlay may now be visible/registered, but they cannot
    # overwrite the target captured before the listening overlay was emitted.
    runtime.set_own_hwnds({99, 100, 101})
    runtime.end_recording()

    assert submitted.wait(1.0)
    assert capture_calls == [target]
    assert runtime._target is target
    assert submission["target"] is target
    assert target.hwnd not in runtime._own_hwnds
    assert overlays[0][0] == "listening"
    assert overlays[0][1]["target_hwnd"] == target.hwnd

    delivered = threading.Event()
    delivery_targets: list[object] = []

    def deliver(_text: str, destination):
        delivery_targets.append(destination)
        delivered.set()
        return {"copied": True, "pasted": True, "reason": ""}

    runtime.injector.deliver = deliver
    job = Job(
        audio=np.ones(16_000, dtype=np.float32),
        info={"seconds": 1.0},
        target=submission["target"],
        mode=str(submission["mode"]),
        tag=str(submission["tag"]),
    )
    runtime._on_engine_result(Result("Hybrid target test", "Hybrid target test", job, 0.1))

    assert delivered.wait(1.0)
    assert delivery_targets == [target]
    assert capture_calls == [target]
