from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any


def _app_data_dir() -> Path:
    """Return an OS-appropriate writable application-data directory."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "EchoType"
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) / "echotype" if xdg else Path.home() / ".local" / "share" / "echotype"


APP_DATA_DIR = _app_data_dir()
SETTINGS_PATH = APP_DATA_DIR / "settings.json"
HISTORY_PATH = APP_DATA_DIR / "history.jsonl"

DEFAULTS: dict[str, Any] = {
    "hotkey_ptt": "shift_r",
    "hotkey_toggle": "f9",
    "hotkey_paste_last": "f11",
    "input_device": None,
    "denoise": True,
    "denoise_strength": 0.75,
    "highpass": True,
    "vad_trim": True,
    "auto_gain": True,
    "auto_paste": True,
    "auto_copy": True,
    "cleanup": True,
    "spoken_punctuation": True,
    "language": "auto",
    "device": "auto",
    "precision": "fp16",
    "min_record_seconds": 0.35,
    "max_record_seconds": 120.0,
    "history_enabled": True,
    "private_session": False,
    "model_revision": None,
    "vocabulary": [
        "EchoType",
        "SraVaani",
        "ARTPARK",
        "IISc",
        "Bengaluru",
        "Kannada",
        "Telugu",
        "Tamil",
        "PyTorch",
        "GitHub",
    ],
}


class Settings:
    """Thread-safe persisted settings with atomic writes.

    Runtime/user data intentionally lives outside the repository so dictation
    history and preferences cannot be committed accidentally.
    """

    def __init__(self, path: Path = SETTINGS_PATH) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._data = deepcopy(DEFAULTS)
        self.load()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> None:
        try:
            if not self._path.exists():
                return
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            with self._lock:
                for key, value in raw.items():
                    if key in DEFAULTS:
                        self._data[key] = value
        except (OSError, ValueError, TypeError):
            # A corrupt preferences file should never stop dictation from
            # starting. Defaults remain in memory and can overwrite it later.
            return

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(".json.tmp")
        with self._lock:
            payload = json.dumps(self._data, indent=2, ensure_ascii=False)
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, self._path)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        if key not in DEFAULTS:
            raise KeyError(f"Unknown EchoType setting: {key}")
        with self._lock:
            self._data[key] = value
        self.save()

    def update(self, values: dict[str, Any]) -> None:
        unknown = set(values) - set(DEFAULTS)
        if unknown:
            raise KeyError(f"Unknown EchoType settings: {sorted(unknown)}")
        with self._lock:
            self._data.update(values)
        self.save()

    def reset(self) -> None:
        with self._lock:
            self._data = deepcopy(DEFAULTS)
        self.save()

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)
