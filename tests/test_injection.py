from __future__ import annotations

from types import SimpleNamespace

from echotype.services import injection


class FakeSettings:
    def __init__(self, **values) -> None:
        self.values = values

    def get(self, key: str, default=None):
        return self.values.get(key, default)


def target(
    *, hwnd: int = 42, title: str = "Notepad", valid: bool = True, sensitive: bool = False
):
    return SimpleNamespace(hwnd=hwnd, title=title, valid=valid, sensitive=sensitive)


def test_empty_delivery_is_a_noop() -> None:
    outcome = injection.Injector(FakeSettings()).deliver("")
    assert outcome == {
        "copied": False,
        "pasted": False,
        "restored": False,
        "target": "",
        "reason": "empty",
    }


def test_copy_without_paste_never_touches_focus_or_keyboard(monkeypatch) -> None:
    copied: list[str] = []
    monkeypatch.setattr(
        injection, "set_clipboard_verified", lambda text: copied.append(text) or True
    )
    monkeypatch.setattr(
        injection,
        "_restore_foreground",
        lambda _hwnd: (_ for _ in ()).throw(AssertionError("focus must not be touched")),
    )
    outcome = injection.Injector(FakeSettings(auto_copy=True, auto_paste=False)).deliver(
        "hello", target=target()
    )
    assert outcome["copied"] is True
    assert outcome["pasted"] is False
    assert outcome["reason"] == "paste_disabled"
    assert copied == ["hello"]


def test_missing_or_own_target_is_not_injected(monkeypatch) -> None:
    monkeypatch.setattr(injection, "set_clipboard_verified", lambda _text: True)
    injector = injection.Injector(
        FakeSettings(auto_copy=True, auto_paste=True), own_hwnds=lambda: {42}
    )
    assert injector.deliver("hello")["reason"] == "no_target"
    assert injector.deliver("hello", target=target())["reason"] == "own_window"


def test_detected_sensitive_target_is_never_pasted(monkeypatch) -> None:
    monkeypatch.setattr(injection, "set_clipboard_verified", lambda _text: True)
    monkeypatch.setattr(
        injection,
        "_restore_foreground",
        lambda _hwnd: (_ for _ in ()).throw(AssertionError("focus must not be changed")),
    )
    outcome = injection.Injector(FakeSettings(auto_copy=True, auto_paste=True)).deliver(
        "do not paste", target=target(sensitive=True)
    )
    assert outcome["pasted"] is False
    assert outcome["reason"] == "sensitive_target"


def test_delivery_helper_sequence_can_be_exercised_without_real_paste(monkeypatch) -> None:
    events: list[object] = []

    def set_clipboard(text: str) -> bool:
        events.append(("clipboard", text))
        return True

    monkeypatch.setattr(injection, "set_clipboard_verified", set_clipboard)
    monkeypatch.setattr(injection, "get_clipboard", lambda: "hello")
    monkeypatch.setattr(
        injection, "_restore_foreground", lambda hwnd: events.append(("focus", hwnd)) or True
    )
    monkeypatch.setattr(injection, "_send_paste", lambda: events.append("paste") or True)
    monkeypatch.setattr(injection.time, "sleep", lambda _seconds: None)

    outcome = injection.Injector(FakeSettings(auto_copy=False, auto_paste=True)).deliver(
        "hello", target=target()
    )

    assert outcome["copied"] is False
    assert outcome["restored"] is True
    assert outcome["pasted"] is True
    assert outcome["reason"] == ""
    assert events == [("clipboard", "hello"), ("focus", 42), "paste"]


def test_failed_paste_uses_type_fallback_without_real_keyboard(monkeypatch) -> None:
    monkeypatch.setattr(injection, "set_clipboard_verified", lambda _text: True)
    monkeypatch.setattr(injection, "get_clipboard", lambda: "hello")
    monkeypatch.setattr(injection, "_restore_foreground", lambda _hwnd: True)
    monkeypatch.setattr(injection, "_send_paste", lambda: False)
    typed: list[str] = []
    monkeypatch.setattr(injection, "type_text", lambda text: typed.append(text) or True)
    monkeypatch.setattr(injection.time, "sleep", lambda _seconds: None)

    outcome = injection.Injector(FakeSettings(auto_copy=False, auto_paste=True)).deliver(
        "hello", target=target()
    )
    assert outcome["pasted"] is True
    assert outcome["reason"] == "typed_fallback"
    assert typed == ["hello"]
