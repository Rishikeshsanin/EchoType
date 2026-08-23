from __future__ import annotations

import platform
import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from echotype import __version__
from echotype.core.audio import SAMPLE_RATE
from echotype.core.transcription import MODEL_REPO, MODEL_REPOS

SENSITIVE_KEY = re.compile(r"token|secret|password|authorization|cookie|api[_-]?key", re.IGNORECASE)
SENSITIVE_VALUE = re.compile(r"(?i)(?:bearer\s+\S+|hf_[A-Za-z0-9]{12,})")


def sanitize_diagnostics(value: Any) -> Any:
    """Recursively remove credentials before diagnostics leave the app."""
    if isinstance(value, Mapping):
        return {
            str(key): "[redacted]" if SENSITIVE_KEY.search(str(key)) else sanitize_diagnostics(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_diagnostics(item) for item in value]
    if isinstance(value, str):
        return SENSITIVE_VALUE.sub("[redacted]", value)
    return deepcopy(value)


class DiagnosticsService:
    """Collect a safe, copyable snapshot of the local EchoType runtime."""

    def __init__(self, settings, *, audio=None, engine=None) -> None:
        self.settings = settings
        self.audio = audio
        self.engine = engine
        self._static = self._collect_static()

    @staticmethod
    def _collect_static() -> dict[str, Any]:
        torch_version = "Not installed"
        cuda_available = False
        gpu = "Not detected"
        try:
            import torch

            torch_version = str(torch.__version__)
            cuda_available = bool(torch.cuda.is_available())
            if cuda_available and torch.cuda.device_count():
                gpu = str(torch.cuda.get_device_name(0))
        except Exception as exc:  # noqa: BLE001 - optional native dependency probe
            torch_version = f"Unavailable ({type(exc).__name__})"
        return {
            "App version": __version__,
            "Python": platform.python_version(),
            "Operating system": platform.platform(),
            "PyTorch": torch_version,
            "CUDA available": cuda_available,
            "GPU": gpu,
        }

    def _microphone(self) -> str:
        selected = self.settings.get("input_device")
        try:
            import sounddevice as sd

            info = (
                sd.query_devices(selected, "input")
                if selected is not None
                else sd.query_devices(kind="input")
            )
            name = str(info.get("name", "Unknown input"))
            native_rate = int(float(info.get("default_samplerate", 0) or 0))
            suffix = f"; native {native_rate} Hz" if native_rate else ""
            return f"{name} (EchoType {SAMPLE_RATE} Hz mono{suffix})"
        except Exception as exc:  # noqa: BLE001 - PortAudio can raise backend-specific errors
            return f"Unavailable ({type(exc).__name__})"

    def _cache(self) -> str:
        try:
            from huggingface_hub import scan_cache_dir

            cache = scan_cache_dir()
            for repo in cache.repos:
                if repo.repo_id in MODEL_REPOS:
                    size_mb = repo.size_on_disk / (1024 * 1024)
                    return f"{repo.repo_id}; {len(repo.revisions)} revision(s), {size_mb:.1f} MiB"
            return "Not found in the Hugging Face cache"
        except Exception:  # noqa: BLE001 - cache scanners expose backend-specific errors
            return "Cache status unavailable"

    def collect(self) -> dict[str, Any]:
        engine = self.engine
        data = {
            **self._static,
            "Microphone": self._microphone(),
            "Requested compute": str(self.settings.get("device", "auto")).upper(),
            "Requested precision": str(self.settings.get("precision", "fp16")).upper(),
            "Runtime device": str(getattr(engine, "device", "Not loaded")).upper(),
            "Runtime precision": str(getattr(engine, "precision", "Not loaded")).upper(),
            "Model status": str(getattr(engine, "status", "Not started")),
            "Model repo": str(getattr(engine, "model_repo", "") or MODEL_REPO),
            "Model revision": str(
                getattr(engine, "model_revision", "")
                or self.settings.get("model_revision")
                or "Not pinned yet"
            ),
            "Model cache": self._cache(),
        }
        return sanitize_diagnostics(data)

    def report(self) -> str:
        data = self.collect()
        lines = ["EchoType diagnostics", "=" * 20]
        lines.extend(f"{key}: {value}" for key, value in data.items())
        lines.append("Audio and transcription run locally after the model is available.")
        return "\n".join(lines)
