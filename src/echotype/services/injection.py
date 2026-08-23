from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import win32api
    import win32clipboard
    import win32con
    import win32gui
    import win32process

    HAVE_WIN32 = True
except Exception:
    HAVE_WIN32 = False


@dataclass(slots=True)
class FocusTarget:
    hwnd: int | None = None
    title: str = ""
    pid: int | None = None
    process_name: str = ""

    @property
    def valid(self) -> bool:
        if not HAVE_WIN32 or not self.hwnd:
            return False
        try:
            return bool(win32gui.IsWindow(self.hwnd))
        except Exception:
            return False

    def __bool__(self) -> bool:
        return self.valid


def capture_focus() -> FocusTarget:
    if not HAVE_WIN32:
        return FocusTarget()
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return FocusTarget()
        title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process_name = ""
        handle = None
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            executable = win32process.GetModuleFileNameEx(handle, 0)
            process_name = Path(executable).name
        except Exception:
            pass
        finally:
            if handle is not None:
                try:
                    win32api.CloseHandle(handle)
                except Exception:
                    pass
        return FocusTarget(hwnd=hwnd, title=title, pid=pid, process_name=process_name)
    except Exception:
        return FocusTarget()


def _nudge_input() -> None:
    if not HAVE_WIN32:
        return
    try:
        vk_menu = 0x12
        win32api.keybd_event(vk_menu, 0, 0, 0)
        win32api.keybd_event(vk_menu, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)
    except Exception:
        pass


def _try_foreground(hwnd: int, *, nudge: bool = False) -> bool:
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        if nudge:
            _nudge_input()

        target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
        current_thread = win32api.GetCurrentThreadId()
        attached = False
        if target_thread and target_thread != current_thread:
            try:
                attached = bool(
                    win32process.AttachThreadInput(current_thread, target_thread, True)
                )
            except Exception:
                attached = False

        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            try:
                win32gui.BringWindowToTop(hwnd)
            except Exception:
                pass
        finally:
            if attached:
                try:
                    win32process.AttachThreadInput(current_thread, target_thread, False)
                except Exception:
                    pass

        for _ in range(20):
            if win32gui.GetForegroundWindow() == hwnd:
                return True
            time.sleep(0.01)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception:
        return False


def _restore_foreground(hwnd: int, attempts: int = 3) -> bool:
    if not HAVE_WIN32 or not hwnd:
        return False
    for attempt in range(attempts):
        if _try_foreground(hwnd, nudge=attempt > 0):
            return True
        time.sleep(0.05)
    return False


def _clipboard_open(retries: int = 12, delay: float = 0.02) -> bool:
    for _ in range(retries):
        try:
            win32clipboard.OpenClipboard()
            return True
        except Exception:
            time.sleep(delay)
    return False


def get_clipboard() -> str | None:
    if not HAVE_WIN32:
        try:
            import pyperclip

            return pyperclip.paste()
        except Exception:
            return None
    if not _clipboard_open():
        return None
    try:
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        return None
    except Exception:
        return None
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def set_clipboard(text: str) -> bool:
    if not HAVE_WIN32:
        try:
            import pyperclip

            pyperclip.copy(text)
            return True
        except Exception:
            return False
    if not _clipboard_open():
        return False
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        return True
    except Exception:
        return False
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


def set_clipboard_verified(text: str, attempts: int = 4) -> bool:
    for _ in range(attempts):
        if set_clipboard(text):
            time.sleep(0.03)
            if get_clipboard() == text:
                return True
        time.sleep(0.05)
    return False


def _send_paste() -> bool:
    try:
        from pynput.keyboard import Controller, Key

        keyboard = Controller()
        with keyboard.pressed(Key.ctrl):
            keyboard.press("v")
            keyboard.release("v")
        return True
    except Exception:
        pass

    if not HAVE_WIN32:
        return False
    try:
        vk_control, vk_v = 0x11, 0x56
        win32api.keybd_event(vk_control, 0, 0, 0)
        win32api.keybd_event(vk_v, 0, 0, 0)
        win32api.keybd_event(vk_v, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(vk_control, 0, win32con.KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False


def type_text(text: str, delay: float = 0.004) -> bool:
    try:
        from pynput.keyboard import Controller

        keyboard = Controller()
        for char in text:
            keyboard.type("\r" if char == "\n" else char)
            time.sleep(delay)
        return True
    except Exception:
        return False


class Injector:
    """Deliver transcripts to the exact app that had focus when speech began."""

    def __init__(self, settings, own_hwnds=None) -> None:
        self.settings = settings
        self.own_hwnds = own_hwnds or (lambda: set())
        self._lock = threading.Lock()

    def is_own_window(self, target: FocusTarget | None) -> bool:
        try:
            return bool(target and target.hwnd in self.own_hwnds())
        except Exception:
            return False

    def deliver(self, text: str, target: FocusTarget | None = None) -> dict[str, object]:
        result: dict[str, object] = {
            "copied": False,
            "pasted": False,
            "restored": False,
            "target": getattr(target, "title", "") or "",
            "reason": "",
        }
        if not text:
            result["reason"] = "empty"
            return result

        if self.settings.get("auto_copy", True):
            result["copied"] = set_clipboard_verified(text)

        if not self.settings.get("auto_paste", True):
            result["reason"] = "paste_disabled"
            return result
        if target is None or not target.valid:
            result["reason"] = "no_target"
            return result
        if self.is_own_window(target):
            result["reason"] = "own_window"
            return result

        with self._lock:
            previous = get_clipboard() if not result["copied"] else None
            if not set_clipboard_verified(text):
                result["reason"] = "clipboard_failed"
                return result

            result["restored"] = _restore_foreground(target.hwnd)
            if not result["restored"]:
                result["reason"] = "focus_failed"
                return result

            time.sleep(0.08)
            if get_clipboard() != text and not set_clipboard_verified(text):
                result["reason"] = "clipboard_changed"
                return result

            result["pasted"] = _send_paste()
            time.sleep(0.06)
            if not result["pasted"]:
                result["pasted"] = type_text(text)
                result["reason"] = "typed_fallback"

            if previous is not None:
                def restore_clipboard() -> None:
                    time.sleep(0.6)
                    set_clipboard(previous)

                threading.Thread(target=restore_clipboard, daemon=True).start()

        return result
