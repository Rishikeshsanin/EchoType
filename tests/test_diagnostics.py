from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from echotype.services.diagnostics import DiagnosticsService, safe_detail
from echotype.services.settings import Settings


def test_diagnostics_redact_tokens_and_user_home() -> None:
    synthetic_token = "hf_" + "1234567890abcdef"
    detail = safe_detail(
        f"failed at C:\\Users\\Alice\\model with HF_TOKEN={synthetic_token}",
        home=Path("C:/Users/Alice"),
    )
    assert synthetic_token not in detail
    assert "C:\\Users\\Alice" not in detail
    assert "<redacted>" in detail
    assert "%USERPROFILE%" in detail


def test_diagnostics_flatten_and_bound_untrusted_exceptions() -> None:
    detail = safe_detail("first line\nBearer abcdefghijklmnop\n" + "x" * 500, limit=80)
    assert "\n" not in detail
    assert "abcdefghijklmnop" not in detail
    assert len(detail) == 80
    assert detail.endswith("…")


def test_diagnostics_expose_measured_ptt_timeline(tmp_path, monkeypatch) -> None:
    settings = Settings(tmp_path / "settings.json")
    runtime = SimpleNamespace(
        capture_stop_latency_ms=0.42,
        capture_timing_ms={
            "ptt_key_down": 0.0,
            "audio_begin": 0.1,
            "ptt_key_up": 800.0,
            "recording_buffer_closed": 800.42,
            "processing_state": 800.8,
        },
    )
    service = DiagnosticsService(settings, runtime=runtime)
    monkeypatch.setattr(service, "_microphone", lambda: "Test microphone")
    monkeypatch.setattr(service, "_cache", lambda: "Test cache")

    report = service.collect()

    assert report["Last PTT stop latency"] == "0.420 ms"
    assert "key-up 800.00" in report["Last PTT timeline (ms)"]
    assert "buffer-closed 800.42" in report["Last PTT timeline (ms)"]
