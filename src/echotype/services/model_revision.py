from __future__ import annotations

import re
from collections.abc import Callable

_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40,64}$")


def immutable_revision(value: object) -> str | None:
    candidate = str(value or "").strip()
    return candidate.lower() if _COMMIT_SHA.fullmatch(candidate) else None


def resolve_persisted_revision(
    repo: str,
    settings,
    *,
    pinned_repo: str,
    model_info: Callable[[str], object],
) -> str | None:
    """Resolve and persist an immutable commit SHA for the configured mirror.

    Moving branch names and malformed persisted values are deliberately not
    accepted as revisions when loading model-provided Python code.
    """

    if repo != pinned_repo:
        return None

    stored = immutable_revision(settings.get("model_revision"))
    if stored:
        return stored

    try:
        revision = immutable_revision(getattr(model_info(repo), "sha", None))
    except Exception:  # noqa: BLE001 - third-party network clients raise varied exceptions
        return None
    if revision:
        settings.set("model_revision", revision)
    return revision
