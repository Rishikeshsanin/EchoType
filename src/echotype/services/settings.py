from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any


def _app_data_dir(
    *,
    os_name: str | None = None,
    environ: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return an OS-appropriate writable application-data directory."""
    platform_name = os_name or os.name
    environment = os.environ if environ is None else environ
    home_dir = home or Path.home()
    if platform_name == "nt":
        base = Path(environment.get("LOCALAPPDATA") or home_dir / "AppData" / "Local")
        return base / "EchoType"
    xdg = environment.get("XDG_DATA_HOME")
    return Path(xdg) / "echotype" if xdg else home_dir / ".local" / "share" / "echotype"


APP_DATA_DIR = _app_data_dir()
SETTINGS_PATH = APP_DATA_DIR / "settings.json"
HISTORY_PATH = APP_DATA_DIR / "history.jsonl"
VOCABULARY_PATH = APP_DATA_DIR / "vocabulary.json"
NOTES_PATH = APP_DATA_DIR / "notes.json"

DEFAULTS: dict[str, Any] = {
    "hotkey_ptt": "shift_r",
    "hotkey_toggle": "f9",
    "hotkey_paste_last": "f11",
    "hotkey_cancel": "esc",
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
    "auto_punctuate": True,
    "default_mode": "smart",
    "language": "auto",
    "device": "auto",
    "precision": "fp16",
    "min_record_seconds": 0.35,
    "max_record_seconds": 120.0,
    "history_enabled": True,
    "private_session": False,
    "history_retention_days": 0,
    "theme": "system",
    "model_revision": None,
    "upstream_model_revision": None,
    # Kept for migration compatibility. New installations and the engine use
    # VocabularyService profiles; older settings files still load safely.
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


def _choice(*choices: str) -> Callable[[Any], str]:
    allowed = set(choices)

    def validate(value: Any) -> str:
        normalized = str(value).strip().lower()
        if normalized not in allowed:
            raise ValueError(f"expected one of {sorted(allowed)}")
        return normalized

    return validate


def _boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError("expected true or false")
    return value


def _number(minimum: float, maximum: float) -> Callable[[Any], float]:
    def validate(value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"expected a number from {minimum} to {maximum}")
        result = float(value)
        if not minimum <= result <= maximum:
            raise ValueError(f"expected a number from {minimum} to {maximum}")
        return result

    return validate


def _integer(minimum: int, maximum: int) -> Callable[[Any], int]:
    def validate(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"expected an integer from {minimum} to {maximum}")
        if not minimum <= value <= maximum:
            raise ValueError(f"expected an integer from {minimum} to {maximum}")
        return value

    return validate


def _input_device(value: Any) -> int | str | None:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    if isinstance(value, str) and value.strip() and len(value) <= 200:
        return value.strip()
    raise ValueError("expected a microphone index, name, or null")


SHORTCUT_PATTERN = re.compile(
    r"^(?:[a-z0-9]|f(?:[1-9]|1[0-2])|(?:ctrl|alt|shift)_[lr]|cmd(?:_r)?|"
    r"caps_lock|scroll_lock|pause|insert|esc)$"
)


def validate_shortcut(value: Any) -> str:
    normalized = str(value).strip().lower()
    if not SHORTCUT_PATTERN.fullmatch(normalized):
        raise ValueError("unsupported shortcut key")
    return normalized


def _language(value: Any) -> str:
    from echotype.core.languages import BY_CODE

    normalized = str(value).strip().lower()
    if normalized not in BY_CODE:
        raise ValueError("unsupported language code")
    return normalized


def _revision(value: Any) -> str | None:
    if value is None or value == "":
        return None
    normalized = str(value).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40,64}", normalized):
        raise ValueError("model revision must be an immutable commit SHA")
    return normalized


def _legacy_vocabulary(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError("expected a vocabulary list")
    if len(value) > 10_000:
        raise ValueError("vocabulary is too large")
    cleaned: list[Any] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip()[:200])
        elif isinstance(item, dict) and str(item.get("term", "")).strip():
            cleaned.append(deepcopy(item))
        else:
            raise ValueError("invalid vocabulary entry")
    return cleaned


VALIDATORS: dict[str, Callable[[Any], Any]] = {
    "hotkey_ptt": validate_shortcut,
    "hotkey_toggle": validate_shortcut,
    "hotkey_paste_last": validate_shortcut,
    "hotkey_cancel": validate_shortcut,
    "input_device": _input_device,
    "denoise": _boolean,
    "denoise_strength": _number(0.0, 1.0),
    "highpass": _boolean,
    "vad_trim": _boolean,
    "auto_gain": _boolean,
    "auto_paste": _boolean,
    "auto_copy": _boolean,
    "cleanup": _boolean,
    "spoken_punctuation": _boolean,
    "auto_punctuate": _boolean,
    "default_mode": _choice("verbatim", "smart", "notes"),
    "language": _language,
    "device": _choice("auto", "cpu", "cuda"),
    "precision": _choice("fp16", "fp32"),
    "min_record_seconds": _number(0.1, 10.0),
    "max_record_seconds": _number(5.0, 3_600.0),
    "history_enabled": _boolean,
    "private_session": _boolean,
    "history_retention_days": _integer(0, 3_650),
    "theme": _choice("system", "dark", "light"),
    "model_revision": _revision,
    "upstream_model_revision": _revision,
    "vocabulary": _legacy_vocabulary,
}


class Settings:
    """Thread-safe validated settings with atomic per-user persistence."""

    def __init__(self, path: Path = SETTINGS_PATH) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._data = deepcopy(DEFAULTS)
        self.load()

    @property
    def path(self) -> Path:
        return self._path

    @staticmethod
    def validate(key: str, value: Any) -> Any:
        if key not in DEFAULTS:
            raise KeyError(f"Unknown EchoType setting: {key}")
        try:
            return VALIDATORS[key](value)
        except ValueError as exc:
            raise ValueError(f"Invalid value for {key}: {exc}") from exc

    def load(self) -> None:
        try:
            if not self._path.exists():
                return
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
        except (OSError, ValueError, TypeError):
            return

        accepted: dict[str, Any] = {}
        for key, value in raw.items():
            if key not in DEFAULTS:
                continue
            try:
                accepted[key] = self.validate(key, value)
            except (TypeError, ValueError):
                # One damaged preference must not invalidate the rest.
                continue
        with self._lock:
            self._data.update(accepted)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        with self._lock:
            payload = json.dumps(self._data, indent=2, ensure_ascii=False)
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, self._path)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return deepcopy(self._data.get(key, DEFAULTS.get(key, default)))

    def set(self, key: str, value: Any) -> None:
        normalized = self.validate(key, value)
        with self._lock:
            self._data[key] = normalized
        self.save()

    def update(self, values: dict[str, Any]) -> None:
        unknown = set(values) - set(DEFAULTS)
        if unknown:
            raise KeyError(f"Unknown EchoType settings: {sorted(unknown)}")
        # Validate the whole update before changing in-memory state.
        normalized = {key: self.validate(key, value) for key, value in values.items()}
        with self._lock:
            self._data.update(normalized)
        self.save()

    def reset(self) -> None:
        with self._lock:
            self._data = deepcopy(DEFAULTS)
        self.save()

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)
