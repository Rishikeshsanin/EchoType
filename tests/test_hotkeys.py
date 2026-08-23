from __future__ import annotations

from echotype.services import hotkeys


class FakeSettings:
    def __init__(self) -> None:
        self.values = {
            "hotkey_ptt": "shift_r",
            "hotkey_toggle": "f9",
            "hotkey_paste_last": "f11",
        }

    def get(self, key: str):
        return self.values[key]


def test_key_resolution_and_labels_are_stable() -> None:
    assert hotkeys.resolve(" shift_r ") == hotkeys.keyboard.Key.shift_r
    assert hotkeys.resolve("F9") == hotkeys.keyboard.Key.f9
    assert hotkeys.resolve("x") == hotkeys.keyboard.KeyCode.from_char("x")
    assert hotkeys.resolve("not-a-key") is None
    assert hotkeys.label_for("shift_r") == "Right Shift"
    assert hotkeys.label_for("f11") == "F11"


def test_direct_hotkey_logic_needs_no_global_listener() -> None:
    events: list[str] = []
    manager = hotkeys.HotkeyManager(
        FakeSettings(),
        on_ptt_down=lambda: events.append("down"),
        on_ptt_up=lambda: events.append("up"),
        on_toggle=lambda: events.append("toggle"),
        on_paste_last=lambda: events.append("paste"),
        on_cancel=lambda: events.append("cancel"),
    )

    manager._press(hotkeys.keyboard.Key.shift_r)
    manager._press(hotkeys.keyboard.Key.shift_r)
    manager._release(hotkeys.keyboard.Key.shift_r)
    manager._release(hotkeys.keyboard.Key.shift_r)
    manager._press(hotkeys.keyboard.Key.f9)
    manager._press(hotkeys.keyboard.Key.f11)
    manager._press(hotkeys.keyboard.Key.esc)

    assert events == ["down", "up", "toggle", "paste", "cancel"]
    assert manager.running is False


def test_ptt_release_callback_fires_exactly_once_after_repeat() -> None:
    releases: list[str] = []
    manager = hotkeys.HotkeyManager(
        FakeSettings(),
        on_ptt_up=lambda: releases.append("released"),
    )

    manager._press(hotkeys.keyboard.Key.shift_r)
    manager._press(hotkeys.keyboard.Key.shift_r)
    manager._release(hotkeys.keyboard.Key.shift_r)
    manager._release(hotkeys.keyboard.Key.shift_r)

    assert releases == ["released"]
