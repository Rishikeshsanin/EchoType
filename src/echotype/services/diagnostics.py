from __future__ import annotations

import re
from pathlib import Path

_SECRET_PATTERNS = (
    (re.compile(r"\bhf_[A-Za-z0-9]{8,}\b"), "<redacted-hf-token>"),
    (
        re.compile(r"(?i)\b(HF_TOKEN|HUGGING_FACE_HUB_TOKEN)\s*([=:])\s*([^\s,;]+)"),
        r"\1\2<redacted>",
    ),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer <redacted>"),
)


def safe_detail(value: object, *, limit: int = 300, home: Path | None = None) -> str:
    """Return a bounded diagnostic string without common credentials or home paths.

    Diagnostics are intended for UI/status output and support logs, not as a
    replacement for structured exception handling. Newlines are flattened so a
    single failure cannot forge additional diagnostic rows.
    """

    text = " ".join(str(value or "").splitlines()).strip()
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)

    user_home = str(home or Path.home())
    if user_home:
        text = re.sub(re.escape(user_home), "%USERPROFILE%", text, flags=re.IGNORECASE)

    bounded = max(int(limit), 0)
    if bounded and len(text) > bounded:
        return text[: max(0, bounded - 1)] + "…"
    return text if bounded else ""
