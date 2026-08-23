from __future__ import annotations

from pathlib import Path

from echotype.services.diagnostics import safe_detail


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
