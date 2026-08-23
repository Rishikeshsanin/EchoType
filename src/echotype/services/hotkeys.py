from __future__ import annotations

import threading

from pynput import keyboard

KEY_ALIASES = {
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "shift_r": keyboard.Key.shift_r,
    "shift_l": keyboard.Key.shift_l,
    "cmd": keyboard.Key.cmd,
    "cmd_r": keyboard.Key.cmd_r,
    "caps_lock": keyboard.Key.caps_lock,
    "scroll_lock": keyboard.Key.scroll_lock,
    "pause": keyboard.Key.pause,
    "insert": keyboard.Key.insert,
    "esc": keyboard.Key.esc,
}
for _number in range(1, 13):
    KEY_ALIASES[f"f{_number}"] = getattr(keyboard.Key, f"f{_number}")

KEY_LABELS = {
    "ctrl_r": "Right Ctrl",
    "ctrl_l": "Left Ctrl",
    "alt_r": "Right Alt",
    "alt_l": "Left Alt",
    "shift_r": "Right Shift",
    "shift_l": "Left Shift",
    "caps_lock": "Caps Lock",
    "scroll_lock": "Scroll Lock",
    "insert": "Insert",
    "pause": "Pause",
    "esc": "Esc",
}


def label_for(name: str | None) -> str:
    normalized = str(name or "").lower()
    return KEY_LABELS.get(normalized, normalized.upper())


def resolve(name: str | None):
    if not name:
        return None
    normalized = str(name).lower().strip()
    if normalized in KEY_ALIASES:
        return KEY_ALIASES[normalized]
    if len(normalized) == 1:
        return keyboard.KeyCode.from_char(normalized)
    return None


def _matches(key, target) -> bool:  # noqa: ANN001
    if target is None or key is None:
        return False
    if isinstance(target, keyboard.Key):
        return key == target
    if isinstance(target, keyboard.KeyCode):
        return isinstance(key, keyboard.KeyCode) and getattr(key, "char", None) == target.char
    return False


class HotkeyManager:
    """Global keyboard listener kept independent from the Qt UI thread."""

    def __init__(
        self,
        settings,
        on_ptt_down=None,
        on_ptt_up=None,
        on_toggle=None,
        on_paste_last=None,
        on_cancel=None,
    ) -> None:
        self.settings = settings
        self.on_ptt_down = on_ptt_down or (lambda: None)
        self.on_ptt_up = on_ptt_up or (lambda: None)
        self.on_toggle = on_toggle or (lambda: None)
        self.on_paste_last = on_paste_last or (lambda: None)
        self.on_cancel = on_cancel or (lambda: None)
        self._listener = None
        self._ptt_held = False
        self._lock = threading.Lock()
        self.last_error: str | None = None
        self.refresh()

    def refresh(self) -> None:
        self._ptt = resolve(self.settings.get("hotkey_ptt"))
        self._toggle = resolve(self.settings.get("hotkey_toggle"))
        self._paste = resolve(self.settings.get("hotkey_paste_last"))
        try:
            cancel = self.settings.get("hotkey_cancel")
        except (KeyError, TypeError):
            cancel = "esc"
        self._cancel = resolve(cancel or "esc")

    def start(self) -> bool:
        self.stop()
        try:
            self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)
            self._listener.daemon = True
            self._listener.start()
            self.last_error = None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self._listener = None
            return False

    def stop(self) -> None:
        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass

    @property
    def running(self) -> bool:
        return self._listener is not None and self._listener.is_alive()

    def _press(self, key) -> None:  # noqa: ANN001
        try:
            if _matches(key, self._ptt):
                with self._lock:
                    if self._ptt_held:
                        return
                    self._ptt_held = True
                self.on_ptt_down()
                return
            if _matches(key, self._toggle):
                self.on_toggle()
                return
            if _matches(key, self._paste):
                self.on_paste_last()
                return
            if _matches(key, self._cancel):
                self.on_cancel()
        except Exception:
            pass

    def _release(self, key) -> None:  # noqa: ANN001
        try:
            if _matches(key, self._ptt):
                with self._lock:
                    if not self._ptt_held:
                        return
                    self._ptt_held = False
                self.on_ptt_up()
        except Exception:
            pass
